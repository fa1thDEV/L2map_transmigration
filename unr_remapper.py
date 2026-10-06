#!/usr/bin/env python3
"""
UNR Package Remapper & Single-Package Isolator
Re-routes all StaticMesh and Texture references in a .unr map to a single unified package per class.
Optionally applies chronicle-level class downgrade and header version patching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ue2_package import UE2Package, ImportEntry


CHRONICLE_PROFILES = {
    "c4": {"version": 123, "license": 28, "name": "Lineage 2 C4 (Scions of Destiny)"},
    "interlude": {"version": 123, "license": 28, "name": "Lineage 2 Interlude (C6)"},
    "c6": {"version": 123, "license": 28, "name": "Lineage 2 Interlude (C6)"},
    "h5": {"version": 123, "license": 36, "name": "Lineage 2 High Five"},
    "classic": {"version": 123, "license": 37, "name": "Lineage 2 Classic"},
}

CLASS_SUBSTITUTIONS = {
    "Spotlight": "Light",
    "AmbientSoundWObject": "AmbientSound",
    "DynamicProjector": "Projector",
}


@dataclass
class RemapReport:
    map_name: str
    target_chronicle: Optional[str]
    target_mesh_pkg: str
    target_tex_pkg: str
    meshes_remapped: List[str] = field(default_factory=list)
    textures_remapped: List[str] = field(default_factory=list)
    classes_downgraded: Dict[str, str] = field(default_factory=dict)
    old_packages_replaced: Set[str] = field(default_factory=set)
    output_path: Optional[Path] = None
    file_size_before: int = 0
    file_size_after: int = 0


class UNRRemapper:
    """Remaps package dependencies within an Unreal Engine 2 map."""

    def __init__(self, map_path: str | Path):
        self.map_path = Path(map_path)
        self.pkg = UE2Package.load_from_file(self.map_path)

    def remap(
        self,
        output_path: str | Path,
        target_mesh_pkg: Optional[str] = None,
        target_tex_pkg: Optional[str] = None,
        target_chronicle: Optional[str] = None,
    ) -> RemapReport:
        stem = self.map_path.stem
        mesh_pkg_name = target_mesh_pkg or f"Map_{stem}_S"
        tex_pkg_name = target_tex_pkg or f"Map_{stem}_T"

        report = RemapReport(
            map_name=self.map_path.name,
            target_chronicle=target_chronicle,
            target_mesh_pkg=mesh_pkg_name,
            target_tex_pkg=tex_pkg_name,
            file_size_before=len(self.pkg.raw_data),
        )

        # 1. Record original packages
        orig_packages = self.pkg.get_imported_packages()

        # 2. Add or find target master packages in imports
        mesh_pkg_import_idx = self._find_or_create_package_import(mesh_pkg_name)
        tex_pkg_import_idx = self._find_or_create_package_import(tex_pkg_name)

        mesh_outer_ref = -(mesh_pkg_import_idx + 1)
        tex_outer_ref = -(tex_pkg_import_idx + 1)

        # 3. Remap StaticMeshes
        for imp in self.pkg.imports:
            if imp.class_name.lower() == "staticmesh":
                if imp.top_package:
                    report.old_packages_replaced.add(imp.top_package)
                imp.package_index = mesh_outer_ref
                report.meshes_remapped.append(imp.object_name)

        # 4. Remap Textures and Shaders
        tex_classes = {
            "texture", "shader", "cubemap", "finalblend", "combiner",
            "colormodifier", "fadecolor", "texpanner", "texrotator",
            "texscaler", "texcoordsource", "texenvmap", "firetexture",
            "fluidtexture", "watertexture", "wettexture"
        }
        for imp in self.pkg.imports:
            if imp.class_name.lower() in tex_classes:
                # Do not remap internal Core/Engine/LineageEffect materials if they are native
                if imp.top_package.lower() not in ("core", "engine"):
                    if imp.top_package:
                        report.old_packages_replaced.add(imp.top_package)
                    imp.package_index = tex_outer_ref
                    report.textures_remapped.append(imp.object_name)

        # 5. Chronicle-level compatibility patching
        target_ver = None
        target_lic = None
        if target_chronicle and target_chronicle.lower() in CHRONICLE_PROFILES:
            prof = CHRONICLE_PROFILES[target_chronicle.lower()]
            target_ver = prof["version"]
            target_lic = prof["license"]

            # If downporting to C4/C6/Interlude (license <= 28), downgrade modern classes
            if target_lic <= 28 or target_chronicle.lower() in ("c4", "interlude", "c6"):
                for imp in self.pkg.imports:
                    if imp.object_name in CLASS_SUBSTITUTIONS:
                        replacement = CLASS_SUBSTITUTIONS[imp.object_name]
                        report.classes_downgraded[imp.object_name] = replacement
                        # Update object name to replacement
                        imp.object_name = replacement
                        imp.object_name_index = self.pkg.add_name(replacement)

        # 6. Save modified package
        out_p = Path(output_path)
        saved_bytes = self.pkg.serialize_tables_and_save(
            out_p,
            target_version=target_ver,
            target_license=target_lic,
        )
        report.output_path = out_p
        report.file_size_after = len(saved_bytes)
        return report

    def _find_or_create_package_import(self, package_name: str) -> int:
        """Finds or creates an import entry for a root Package."""
        for imp in self.pkg.imports:
            if imp.class_name.lower() == "package" and imp.package_index == 0:
                if imp.object_name.lower() == package_name.lower():
                    return imp.index

        return self.pkg.add_import(
            class_package="Core",
            class_name="Package",
            package_index=0,
            object_name=package_name,
        )


def format_remap_report(rep: RemapReport) -> str:
    lines = [
        f"# Single-Package Isolation Report: {rep.map_name}",
        "",
        "## Summary",
        f"- **Target Map:** `{rep.map_name}`",
        f"- **Target Chronicle Profile:** `{rep.target_chronicle.upper() if rep.target_chronicle else 'Preserve Version'}`",
        f"- **Consolidated Mesh Package:** `{rep.target_mesh_pkg}.usx`",
        f"- **Consolidated Texture Package:** `{rep.target_tex_pkg}.utx`",
        f"- **Meshes Remapped:** {len(rep.meshes_remapped):,} StaticMesh references",
        f"- **Textures/Shaders Remapped:** {len(rep.textures_remapped):,} Texture references",
        f"- **External Packages Consolidated:** {len(rep.old_packages_replaced):,} packages into 2 files",
        f"- **Output Map Size:** {rep.file_size_after / (1024*1024):.2f} MB",
        "",
        f"## Classes Downgraded for Compatibility ({len(rep.classes_downgraded)})",
    ]
    if rep.classes_downgraded:
        for orig, repl in rep.classes_downgraded.items():
            lines.append(f"- `{orig}` -> `{repl}`")
    else:
        lines.append("- None (Native engine compatibility)")

    lines.extend([
        "",
        f"## Packages Replaced & Consolidated ({len(rep.old_packages_replaced)})",
    ])
    for p in sorted(rep.old_packages_replaced):
        lines.append(f"- `{p}`")

    return "\n".join(lines) + "\n"
