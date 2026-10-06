#!/usr/bin/env python3
"""
USX Package Consolidator
Bundles all 3D StaticMesh models required by a map into a single,
unified Map_{SECTOR}_S.usx package, redirecting their material imports to Map_{SECTOR}_T.
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
class USXConsolidationReport:
    target_package_name: str
    output_path: Path
    total_meshes_requested: int
    total_meshes_bundled: int
    missing_meshes: List[str] = field(default_factory=list)
    source_packages_read: Set[str] = field(default_factory=set)
    file_size_bytes: int = 0


class USXConsolidator:
    """Consolidates scattered StaticMesh assets into a single UE2 .usx package."""

    def __init__(self, client_root: str | Path):
        self.client_root = Path(client_root)
        self.mesh_dir = self.client_root / "StaticMeshes"
        self._pkg_cache: Dict[str, UE2Package] = {}

    def _get_package(self, pkg_name: str) -> Optional[UE2Package]:
        key = pkg_name.lower()
        if key in self._pkg_cache:
            return self._pkg_cache[key]

        target_file = self.mesh_dir / f"{pkg_name}.usx"
        if not target_file.exists():
            matches = list(self.mesh_dir.glob(f"{pkg_name}.*"))
            if matches:
                target_file = matches[0]
            else:
                return None

        try:
            pkg = UE2Package.load_from_file(target_file)
            self._pkg_cache[key] = pkg
            return pkg
        except Exception:
            return None

    def consolidate(
        self,
        unr_path: str | Path,
        output_path: str | Path,
        target_tex_pkg: Optional[str] = None,
        target_chronicle: Optional[str] = None,
    ) -> USXConsolidationReport:
        unr_p = Path(unr_path)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        sector_name = unr_p.stem
        tex_pkg_name = target_tex_pkg or f"Map_{sector_name}_T"

        analyzer = UNRAnalyzer(client_root=self.client_root)
        unr_res = analyzer.analyze_map(unr_p, deep_mesh_scan=False)

        all_mesh_refs: Set[str] = set(unr_res.static_meshes_used)

        report = USXConsolidationReport(
            target_package_name=out_p.stem,
            output_path=out_p,
            total_meshes_requested=len(all_mesh_refs),
            total_meshes_bundled=0,
        )

        # Group requested meshes by source package
        pkg_to_names: Dict[str, Set[str]] = {}
        for ref in all_mesh_refs:
            parts = ref.split(".")
            pkg_name = parts[0]
            obj_name = parts[-1]
            pkg_to_names.setdefault(pkg_name, set()).add(obj_name)

        # Base names
        names: List[str] = ["None", "Core", "Engine", "Package", "Class", "StaticMesh", tex_pkg_name]
        name_flags: List[int] = [0x00070010] * len(names)

        def add_name(n: str, flg: int = 0x00070010) -> int:
            for idx, existing in enumerate(names):
                if existing.lower() == n.lower():
                    return idx
            idx = len(names)
            names.append(n)
            name_flags.append(flg)
            return idx

        # Imports:
        # Import 0: Core.Package (root)
        # Import 1: Core.Class.StaticMesh
        # Import 2: Core.Package (target texture package)
        imports_raw = bytearray()
        # Import 0: Core.Package
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Package")))
        imports_raw.extend(struct.pack("<i", 0))
        imports_raw.extend(write_compact_index(add_name("Core")))

        # Import 1: Core.Class.StaticMesh
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Class")))
        imports_raw.extend(struct.pack("<i", 0))
        imports_raw.extend(write_compact_index(add_name("StaticMesh")))

        # Import 2: Core.Package (tex_pkg_name)
        imports_raw.extend(write_compact_index(add_name("Core")))
        imports_raw.extend(write_compact_index(add_name("Package")))
        imports_raw.extend(struct.pack("<i", 0))
        imports_raw.extend(write_compact_index(add_name(tex_pkg_name)))

        out_buf = bytearray(b"\x00" * 64)
        export_records: List[Tuple[str, int, int]] = []
        bundled_count = 0

        for pkg_name, obj_names in pkg_to_names.items():
            src_pkg = self._get_package(pkg_name)
            if not src_pkg:
                for missing in obj_names:
                    report.missing_meshes.append(f"{pkg_name}.{missing}")
                continue

            report.source_packages_read.add(pkg_name)

            for exp in src_pkg.exports:
                if exp.object_name.lower() in {o.lower() for o in obj_names}:
                    raw_data = src_pkg.raw_data[exp.serial_offset : exp.serial_offset + exp.serial_size]
                    if not raw_data:
                        continue

                    obj_offset = len(out_buf)
                    out_buf.extend(raw_data)
                    export_records.append((exp.object_name, obj_offset, len(raw_data)))
                    add_name(exp.object_name)
                    bundled_count += 1

        report.total_meshes_bundled = bundled_count

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
        for obj_name, off, sz in export_records:
            name_idx = add_name(obj_name)
            export_raw.extend(write_compact_index(-2))  # Import 1 (StaticMesh class)
            export_raw.extend(write_compact_index(0))   # Super
            export_raw.extend(struct.pack("<i", 0))     # Outer (root)
            export_raw.extend(write_compact_index(name_idx))
            export_raw.extend(struct.pack("<I", 0x00020001))  # RF_Public | RF_LoadForClient
            export_raw.extend(write_compact_index(sz))
            export_raw.extend(write_compact_index(off))
        out_buf.extend(export_raw)

        # Chronicle version
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
            3,  # import count
            import_offset,
        )

        # Write Generations
        struct.pack_into("<I", out_buf, 52, 1)
        struct.pack_into("<II", out_buf, 56, len(export_records), len(names))

        out_p.write_bytes(bytes(out_buf))
        report.file_size_bytes = len(out_buf)
        return report
