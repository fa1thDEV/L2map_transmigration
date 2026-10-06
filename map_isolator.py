#!/usr/bin/env python3
"""
Map Isolator & Single-Package Transmigration Pipeline
Executes end-to-end isolation for a Lineage 2 map sector:
  1. Consolidates all required StaticMeshes into StaticMeshes/Map_{SECTOR}_S.usx
  2. Consolidates all required Textures/Heightmaps into Textures/Map_{SECTOR}_T.utx
  3. Remaps .unr references and applies chronicle compatibility into Maps/{SECTOR}.unr
  4. Generates an exhaustive Transmigration Manifest.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from unr_remapper import UNRRemapper, RemapReport
from utx_consolidator import UTXConsolidator, UTXConsolidationReport
from usx_consolidator import USXConsolidator, USXConsolidationReport


@dataclass
class MapIsolationResult:
    sector_name: str
    target_chronicle: str
    output_dir: Path
    remapped_unr_path: Path
    consolidated_usx_path: Path
    consolidated_utx_path: Path
    remap_report: RemapReport
    usx_report: USXConsolidationReport
    utx_report: UTXConsolidationReport
    elapsed_seconds: float = 0.0


class MapIsolator:
    """End-to-end engine for Single-Package Map Isolation."""

    def __init__(self, client_root: str | Path):
        self.client_root = Path(client_root)

    def isolate_map(
        self,
        unr_path: str | Path | List[str | Path],
        output_dir: str | Path,
        target_chronicle: str = "interlude",
        target_mesh_pkg: Optional[str] = None,
        target_tex_pkg: Optional[str] = None,
        encrypt_output: Optional[int] = None,
    ) -> MapIsolationResult:
        start_time = time.time()
        unr_list = [Path(p) for p in unr_path] if isinstance(unr_path, (list, tuple)) else [Path(unr_path)]
        out_base = Path(output_dir)

        sector = unr_list[0].stem.replace("_Classic", "").replace("_classic", "")
        mesh_pkg = target_mesh_pkg or f"Map_{sector}_S"
        tex_pkg = target_tex_pkg or f"Map_{sector}_T"

        # Output subdirectories
        maps_dir = out_base / "Maps"
        static_meshes_dir = out_base / "StaticMeshes"
        textures_dir = out_base / "Textures"

        maps_dir.mkdir(parents=True, exist_ok=True)
        static_meshes_dir.mkdir(parents=True, exist_ok=True)
        textures_dir.mkdir(parents=True, exist_ok=True)

        out_usx = static_meshes_dir / f"{mesh_pkg}.usx"
        out_utx = textures_dir / f"{tex_pkg}.utx"

        # Step 1: Consolidate Textures for all input maps
        print(f"[1/3] Consolidating textures into {out_utx.name}...")
        utx_builder = UTXConsolidator(client_root=self.client_root)
        utx_rep = utx_builder.consolidate(
            unr_path=unr_list,
            output_path=out_utx,
            target_chronicle=target_chronicle,
        )
        print(f"      -> {utx_rep.total_textures_bundled} textures bundled ({utx_rep.file_size_bytes / (1024*1024):.2f} MB)")

        # Step 2: Consolidate StaticMeshes for all input maps
        print(f"[2/3] Consolidating static meshes into {out_usx.name}...")
        usx_builder = USXConsolidator(client_root=self.client_root)
        usx_rep = usx_builder.consolidate(
            unr_path=unr_list,
            output_path=out_usx,
            target_tex_pkg=tex_pkg,
            target_chronicle=target_chronicle,
        )
        print(f"      -> {usx_rep.total_meshes_bundled} meshes bundled ({usx_rep.file_size_bytes / (1024*1024):.2f} MB)")

        # Step 3: Remap each input UNR map
        print(f"[3/3] Remapping {len(unr_list)} .unr map(s) and patching for {target_chronicle.upper()}...")
        out_unrs: List[Path] = []
        last_remap_rep = None
        for u_path in unr_list:
            out_unr = maps_dir / u_path.name
            remapper = UNRRemapper(u_path)
            last_remap_rep = remapper.remap(
                output_path=out_unr,
                target_mesh_pkg=mesh_pkg,
                target_tex_pkg=tex_pkg,
                target_chronicle=target_chronicle,
            )
            out_unrs.append(out_unr)
            print(f"      -> Remapped {u_path.name}: {len(last_remap_rep.meshes_remapped)} meshes, {len(last_remap_rep.textures_remapped)} textures")
            if last_remap_rep.classes_downgraded:
                print(f"         ({len(last_remap_rep.classes_downgraded)} classes downgraded)")

        # Optional Step 4: Lineage 2 Header Encryption (e.g. Lineage2Ver111 for maps/meshes, Lineage2Ver121 for textures)
        if encrypt_output:
            from l2_crypt import encrypt_package_file
            # Lineage 2 Classic l2.exe enforces Lineage2Ver121 (0x79) for all .utx texture packages
            # at VA 0x1090EE15. If a .utx is Ver111, the client displays 'Files are corrupted!!!!'.
            # Meanwhile, .unr maps and .usx static meshes accept Lineage2Ver111 (or raw).
            utx_ver = 121 if encrypt_output in (111, 120, 121) else encrypt_output
            print(f"      -> Encrypting .unr/.usx packages with Lineage2Ver{encrypt_output:03d} and .utx with Lineage2Ver{utx_ver:03d}...")
            for u in out_unrs:
                encrypt_package_file(u, u, version=encrypt_output)
            encrypt_package_file(out_usx, out_usx, version=encrypt_output)
            encrypt_package_file(out_utx, out_utx, version=utx_ver)

        elapsed = time.time() - start_time

        result = MapIsolationResult(
            sector_name=sector,
            target_chronicle=target_chronicle,
            output_dir=out_base,
            remapped_unr_path=out_unrs[0],
            consolidated_usx_path=out_usx,
            consolidated_utx_path=out_utx,
            remap_report=last_remap_rep,
            usx_report=usx_rep,
            utx_report=utx_rep,
            elapsed_seconds=elapsed,
        )

        # Generate markdown manifest
        manifest_md = self.generate_isolation_manifest(result)
        manifest_path = out_base / f"TRANSMIGRATION_{sector}.md"
        manifest_path.write_text(manifest_md, encoding="utf-8")
        print(f"[DONE] Single-Package Isolation completed in {elapsed:.2f}s!")
        print(f"       Manifest saved to: {manifest_path}\n")

        return result

    def generate_isolation_manifest(self, res: MapIsolationResult) -> str:
        lines = [
            f"# Single-Package Transmigration Manifest: Sector `{res.sector_name}`",
            "",
            "## 1. Overview & Portability Status",
            "This map sector has been fully consolidated into **3 autonomous files**.",
            "It can be deployed to any Lineage 2 client without overwriting retail packages or causing dependency conflicts.",
            "",
            "| Deployment Asset | Path in Game Client | Size | Details |",
            "| :--- | :--- | :---: | :--- |",
            f"| **Remapped Map** | `Maps/{res.remapped_unr_path.name}` | {res.remap_report.file_size_after / (1024*1024):.2f} MB | References unified `{res.remap_report.target_mesh_pkg}` and `{res.remap_report.target_tex_pkg}` |",
            f"| **Consolidated Meshes** | `StaticMeshes/{res.consolidated_usx_path.name}` | {res.usx_report.file_size_bytes / (1024*1024):.2f} MB | {res.usx_report.total_meshes_bundled} 3D static models |",
            f"| **Consolidated Textures** | `Textures/{res.consolidated_utx_path.name}` | {res.utx_report.file_size_bytes / (1024*1024):.2f} MB | {res.utx_report.total_textures_bundled} textures & heightmaps |",
            "",
            f"**Target Chronicle Profile:** `{res.target_chronicle.upper()}`",
            f"**Processing Time:** `{res.elapsed_seconds:.2f} seconds`",
            "",
            f"## 2. Chronicle Compatibility & Downgraded Classes ({len(res.remap_report.classes_downgraded)})",
        ]
        if res.remap_report.classes_downgraded:
            lines.append("| Original Modern Class | Substituted Target Class | Reason |")
            lines.append("| :--- | :--- | :--- |")
            for orig, repl in res.remap_report.classes_downgraded.items():
                lines.append(f"| `{orig}` | `{repl}` | Missing in target engine DLL |")
        else:
            lines.append("- None (Native engine compatibility verified).")

        lines.extend([
            "",
            f"## 3. Original Packages Replaced & Consolidated ({len(res.remap_report.old_packages_replaced)})",
            "The following packages from the source client are **no longer needed** by the destination client:",
        ])
        for p in sorted(res.remap_report.old_packages_replaced):
            lines.append(f"- `+{p}`")

        lines.extend([
            "",
            "## 4. Client Installation Instructions",
            "To install this map into any target game client:",
            "1. Copy `Maps/" + res.remapped_unr_path.name + "` into your client's `Maps/` folder.",
            "2. Copy `StaticMeshes/" + res.consolidated_usx_path.name + "` into your client's `StaticMeshes/` folder.",
            "3. Copy `Textures/" + res.consolidated_utx_path.name + "` into your client's `Textures/` folder.",
            "4. Launch the game or test with `L2.exe` / `L2Editor`.",
            "",
        ])
        return "\n".join(lines)
