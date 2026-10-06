#!/usr/bin/env python3
"""
UTX Package Consolidator
Bundles all textures and shaders required by a map and its static meshes
into a single, unified Map_{SECTOR}_T.utx package.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ue2_package import UE2Package, write_compact_index
from unr_analyzer import UNRAnalyzer


CHRONICLE_PROFILES = {
    "c4": {"version": 123, "license": 28},
    "interlude": {"version": 123, "license": 28},
    "c6": {"version": 123, "license": 28},
    "h5": {"version": 123, "license": 36},
    "classic": {"version": 123, "license": 37},
}


@dataclass
class UTXConsolidationReport:
    target_package_name: str
    output_path: Path
    total_textures_requested: int
    total_textures_bundled: int
    missing_textures: List[str] = field(default_factory=list)
    source_packages_read: Set[str] = field(default_factory=set)
    file_size_bytes: int = 0


class UTXConsolidator:
    """Consolidates scattered texture assets into a single UE2 .utx package."""

    def __init__(self, client_root: str | Path):
        self.client_root = Path(client_root)
        self.tex_dirs = [
            self.client_root / "Textures",
            self.client_root / "SysTextures",
        ]
        self._pkg_cache: Dict[str, UE2Package] = {}

    def _get_package(self, pkg_name: str) -> Optional[UE2Package]:
        key = pkg_name.lower()
        if key in self._pkg_cache:
            return self._pkg_cache[key]

        target_file = None
        for d in self.tex_dirs:
            if not d.exists():
                continue
            f = d / f"{pkg_name}.utx"
            if f.exists():
                target_file = f
                break
            matches = list(d.glob(f"{pkg_name}.*"))
            if matches:
                target_file = matches[0]
                break

        if not target_file:
            return None

        try:
            pkg = UE2Package.load_from_file(target_file)
            self._pkg_cache[key] = pkg
            return pkg
        except Exception:
            return None

    def consolidate(
        self,
        unr_path: str | Path | List[str | Path],
        output_path: str | Path,
        target_chronicle: Optional[str] = None,
    ) -> UTXConsolidationReport:
        unr_list = [Path(p) for p in unr_path] if isinstance(unr_path, (list, tuple)) else [Path(unr_path)]
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        analyzer = UNRAnalyzer(client_root=self.client_root)
        all_tex_refs: Set[str] = set()

        for unr_p in unr_list:
            unr_res = analyzer.analyze_map(unr_p, deep_mesh_scan=True)
            for t in unr_res.textures_used:
                all_tex_refs.add(t)
            for s in unr_res.shaders_used:
                all_tex_refs.add(s)

            # Add heightmap texture if present
            sector_name = unr_p.stem.replace("_Classic", "").replace("_classic", "")
            all_tex_refs.add(f"T_{sector_name}.Height.{sector_name}")
            all_tex_refs.add(f"T_{sector_name}.{sector_name}")

        report = UTXConsolidationReport(
            target_package_name=out_p.stem,
            output_path=out_p,
            total_textures_requested=len(all_tex_refs),
            total_textures_bundled=0,
        )

        # Group requested textures by package
        pkg_to_names: Dict[str, Set[str]] = {}
        for ref in all_tex_refs:
            parts = ref.split(".")
            pkg_name = parts[0]
            obj_name = parts[-1]
            pkg_to_names.setdefault(pkg_name, set()).add(obj_name)

        # Package builder structures
        names: List[str] = ["None", "Core", "Engine", "Package", "Class", "Texture", "Shader", "ColorModifier"]
        name_flags: List[int] = [0x00070010] * len(names)

        def add_name(n: str, flg: int = 0x00070010) -> int:
            for idx, existing in enumerate(names):
                if existing.lower() == n.lower():
                    return idx
            idx = len(names)
            names.append(n)
            name_flags.append(flg)
            return idx

        # Imports table:
        # Import 0: Core.Package Engine (root package)
        # Import 1: Core.Class Texture (outer = -1 -> Engine)
        # Import 2: Core.Class Shader (outer = -1 -> Engine)
        # Import 3: Core.Class ColorModifier (outer = -1 -> Engine)
        imports_raw = bytearray()
        # Import 0: Core.Package Engine
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Package")))
        imports_raw.extend(struct.pack("<i", 0))
        imports_raw.extend(write_compact_index(add_name("Engine")))

        # Import 1: Core.Class Texture
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Class")))
        imports_raw.extend(struct.pack("<i", -1))
        imports_raw.extend(write_compact_index(add_name("Texture")))

        # Import 2: Core.Class Shader
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Class")))
        imports_raw.extend(struct.pack("<i", -1))
        imports_raw.extend(write_compact_index(add_name("Shader")))

        # Import 3: Core.Class ColorModifier
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Class")))
        imports_raw.extend(struct.pack("<i", -1))
        imports_raw.extend(write_compact_index(add_name("ColorModifier")))

        # Buffer for new package
        out_buf = bytearray(b"\x00" * 64)
        export_records: List[Tuple[str, int, int, str]] = []  # (name, offset, size, class_type)
        bundled_count = 0

        for pkg_name, obj_names in pkg_to_names.items():
            src_pkg = self._get_package(pkg_name)
            if not src_pkg:
                for missing in obj_names:
                    report.missing_textures.append(f"{pkg_name}.{missing}")
                continue

            report.source_packages_read.add(pkg_name)

            for exp in src_pkg.exports:
                if exp.object_name.lower() in {o.lower() for o in obj_names}:
                    raw_data = src_pkg.raw_data[exp.serial_offset : exp.serial_offset + exp.serial_size]
                    if not raw_data:
                        continue

                    obj_offset = len(out_buf)
                    out_buf.extend(raw_data)

                    # Determine class from source export
                    cls_name = "texture"
                    if exp.class_index < 0:
                        src_imp_idx = -(exp.class_index + 1)
                        if 0 <= src_imp_idx < len(src_pkg.imports):
                            cls_name = src_pkg.imports[src_imp_idx].object_name.lower()

                    export_records.append((exp.object_name, obj_offset, len(raw_data), cls_name))
                    add_name(exp.object_name)
                    bundled_count += 1

        report.total_textures_bundled = bundled_count

        # Build NameTable
        name_offset = len(out_buf)
        name_raw = bytearray()
        for idx, n in enumerate(names):
            nb = n.encode("latin1", errors="replace")
            name_raw.extend(write_compact_index(len(nb) + 1))
            name_raw.extend(nb)
            name_raw.append(0)
            flg = name_flags[idx] if idx < len(name_flags) else 0x00070010
            name_raw.extend(struct.pack("<I", flg))
        out_buf.extend(name_raw)

        # Build ImportTable
        import_offset = len(out_buf)
        out_buf.extend(imports_raw)

        # Build ExportTable
        export_offset = len(out_buf)
        export_raw = bytearray()
        for obj_name, off, sz, cls_name in export_records:
            name_idx = add_name(obj_name)
            if cls_name == "shader":
                class_ref = -3  # Import 2: Shader
            elif cls_name == "colormodifier":
                class_ref = -4  # Import 3: ColorModifier
            else:
                class_ref = -2  # Import 1: Texture

            export_raw.extend(write_compact_index(class_ref))
            export_raw.extend(write_compact_index(0))   # Super
            export_raw.extend(struct.pack("<i", 0))     # Package outer (root)
            export_raw.extend(write_compact_index(name_idx))
            export_raw.extend(struct.pack("<I", 0x000F0004))  # RF_Public | RF_Standalone | RF_LoadForClient | RF_LoadForServer | RF_LoadForEdit
            export_raw.extend(write_compact_index(sz))
            export_raw.extend(write_compact_index(off))
        out_buf.extend(export_raw)

        # Target version
        ver = 123
        lic = 37
        if target_chronicle and target_chronicle.lower() in CHRONICLE_PROFILES:
            ver = CHRONICLE_PROFILES[target_chronicle.lower()]["version"]
            lic = CHRONICLE_PROFILES[target_chronicle.lower()]["license"]

        # Write Header (bytes 0..36)
        struct.pack_into(
            "<IHHIIIIIII",
            out_buf,
            0,
            0x9E2A83C1,
            ver,
            lic,
            1,  # flags: PKG_AllowDownload
            len(names),
            name_offset,
            len(export_records),
            export_offset,
            4,  # import count (Engine, Texture, Shader, ColorModifier)
            import_offset,
        )

        # Write Generations
        struct.pack_into("<I", out_buf, 52, 1)
        struct.pack_into("<II", out_buf, 56, len(export_records), len(names))

        out_p.write_bytes(bytes(out_buf))
        report.file_size_bytes = len(out_buf)
        return report
