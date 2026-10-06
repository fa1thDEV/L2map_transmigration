#!/usr/bin/env python3
"""
UNR Map Dependency Analyzer
Performs shallow and deep analysis of Unreal Engine 2 / Lineage 2 .unr map packages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple

from ue2_package import UE2Package, ImportEntry


@dataclass
class ResolvedPackage:
    name: str
    category: str  # 'StaticMeshes', 'Textures', 'SysTextures', 'Sounds', 'Animations', 'Scripts', 'Unknown'
    expected_extension: str
    found: bool = False
    file_path: Optional[Path] = None
    file_size: int = 0
    direct: bool = True  # True if directly referenced by UNR, False if pulled by a mesh
    referenced_by: List[str] = field(default_factory=list)
    imported_assets: List[str] = field(default_factory=list)


@dataclass
class MapAnalysisResult:
    map_name: str
    map_path: Path
    map_size: int
    unreal_version: int
    licensee_mode: int
    l2_crypt_version: int

    total_names: int
    total_imports: int
    total_exports: int

    # Categories
    static_mesh_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)
    texture_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)
    sound_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)
    animation_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)
    script_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)
    other_packages: Dict[str, ResolvedPackage] = field(default_factory=dict)

    # Detailed asset references
    static_meshes_used: List[str] = field(default_factory=list)
    textures_used: List[str] = field(default_factory=list)
    shaders_used: List[str] = field(default_factory=list)
    sounds_used: List[str] = field(default_factory=list)

    # Missing files
    missing_packages: List[str] = field(default_factory=list)

    def all_packages(self) -> Dict[str, ResolvedPackage]:
        all_pkgs: Dict[str, ResolvedPackage] = {}
        all_pkgs.update(self.static_mesh_packages)
        all_pkgs.update(self.texture_packages)
        all_pkgs.update(self.sound_packages)
        all_pkgs.update(self.animation_packages)
        all_pkgs.update(self.script_packages)
        all_pkgs.update(self.other_packages)
        return all_pkgs


class UNRAnalyzer:
    """Analyzes UNR maps and discovers all dependencies."""

    COMMON_SCRIPTS = {"engine", "core", "gameplay", "lineageeffect", "fire", "ipdrv", "ubrowser"}
    COMMON_SOUNDS = {"ambsound", "ambsound2", "ambsound3", "ambsound4", "itemsound", "itemsound2", "skillsound", "sound"}

    def __init__(self, client_root: Optional[Path | str] = None):
        self.client_root = Path(client_root) if client_root else None

    def analyze_map(self, map_path: Path | str, deep_mesh_scan: bool = True) -> MapAnalysisResult:
        p = Path(map_path)
        if not p.exists():
            raise FileNotFoundError(f"Map file not found: {p}")

        pkg = UE2Package.load_from_file(p)

        res = MapAnalysisResult(
            map_name=p.name,
            map_path=p,
            map_size=p.stat().st_size,
            unreal_version=pkg.summary.file_version,
            licensee_mode=pkg.summary.licensee_mode,
            l2_crypt_version=pkg.l2_version,
            total_names=len(pkg.names),
            total_imports=len(pkg.imports),
            total_exports=len(pkg.exports),
        )

        # Classify individual imported assets
        for imp in pkg.imports:
            cls_lower = imp.class_name.lower()
            if cls_lower == "staticmesh":
                res.static_meshes_used.append(imp.full_path)
            elif cls_lower in ("texture", "cubemap", "fractaltexture", "colormodifier"):
                res.textures_used.append(imp.full_path)
            elif cls_lower == "shader":
                res.shaders_used.append(imp.full_path)
            elif cls_lower in ("sound", "ambientsound"):
                res.sounds_used.append(imp.full_path)

        # Categorize top-level packages
        imported_pkg_names = pkg.get_imported_packages()
        for pkg_name in imported_pkg_names:
            resolved = self._classify_package(pkg_name, direct=True, referrer=p.name)
            self._add_to_result(res, resolved)

            # Record which specific assets came from this package
            for imp in pkg.imports:
                if imp.top_package.lower() == pkg_name.lower() and imp.full_path != pkg_name:
                    resolved.imported_assets.append(imp.full_path)

        # Deep scan: scan .usx files to find textures used by StaticMeshes
        if deep_mesh_scan and self.client_root:
            self._perform_deep_mesh_scan(res)

        # Resolve physical locations and missing status
        if self.client_root:
            self._resolve_disk_files(res)

        return res

    def _classify_package(self, pkg_name: str, direct: bool = True, referrer: str = "") -> ResolvedPackage:
        name_lower = pkg_name.lower()

        # Check by name conventions
        if name_lower in self.COMMON_SCRIPTS or name_lower.endswith(".u"):
            cat = "Scripts"
            ext = ".u"
        elif any(name_lower.startswith(s) for s in ("ambsound", "itemsound", "skillsound", "sound")):
            cat = "Sounds"
            ext = ".uax"
        elif name_lower.endswith("_s") or "staticmesh" in name_lower or name_lower.endswith("_mesh"):
            cat = "StaticMeshes"
            ext = ".usx"
        elif (
            name_lower.endswith("_t")
            or name_lower.startswith("t_")
            or "texture" in name_lower
            or "skies" in name_lower
        ):
            cat = "Textures"
            ext = ".utx"
        elif name_lower.endswith("_a") or "anim" in name_lower:
            cat = "Animations"
            ext = ".ukx"
        else:
            # Ambiguous: if client root available, check file system
            cat, ext = self._detect_category_from_disk(pkg_name)

        item = ResolvedPackage(
            name=pkg_name,
            category=cat,
            expected_extension=ext,
            direct=direct,
        )
        if referrer:
            item.referenced_by.append(referrer)
        return item

    def _detect_category_from_disk(self, pkg_name: str) -> Tuple[str, str]:
        if not self.client_root:
            return "Textures", ".utx"  # Default assumption for unknown assets

        candidates = [
            ("StaticMeshes", ".usx"),
            ("Textures", ".utx"),
            ("SysTextures", ".utx"),
            ("Sounds", ".uax"),
            ("Animations", ".ukx"),
            ("system", ".u"),
        ]
        for folder, ext in candidates:
            cand_path = self.client_root / folder / f"{pkg_name}{ext}"
            if cand_path.exists():
                cat = "Scripts" if folder == "system" else folder
                return cat, ext

        return "Textures", ".utx"

    def _add_to_result(self, res: MapAnalysisResult, pkg: ResolvedPackage):
        cat = pkg.category
        if cat == "StaticMeshes":
            target = res.static_mesh_packages
        elif cat in ("Textures", "SysTextures"):
            target = res.texture_packages
        elif cat == "Sounds":
            target = res.sound_packages
        elif cat == "Animations":
            target = res.animation_packages
        elif cat == "Scripts":
            target = res.script_packages
        else:
            target = res.other_packages

        if pkg.name not in target:
            target[pkg.name] = pkg
        else:
            # Merge referrer
            for r in pkg.referenced_by:
                if r not in target[pkg.name].referenced_by:
                    target[pkg.name].referenced_by.append(r)

    def _perform_deep_mesh_scan(self, res: MapAnalysisResult):
        """Scans referenced StaticMesh .usx packages to discover textures used by the 3D models."""
        for mesh_pkg_name in list(res.static_mesh_packages.keys()):
            mesh_file = self._find_client_file("StaticMeshes", f"{mesh_pkg_name}.usx")
            if not mesh_file or not mesh_file.exists():
                continue

            try:
                mesh_pkg = UE2Package.load_from_file(mesh_file)
                # Find textures/shaders/materials imported by the mesh package
                for sub_pkg_name in mesh_pkg.get_imported_packages():
                    # If it's a texture package not yet registered, add it
                    if sub_pkg_name not in res.texture_packages and sub_pkg_name not in res.script_packages:
                        resolved = self._classify_package(
                            sub_pkg_name,
                            direct=False,
                            referrer=f"Mesh: {mesh_pkg_name}.usx",
                        )
                        self._add_to_result(res, resolved)

                    # Also link references
                    if sub_pkg_name in res.texture_packages:
                        ref_str = f"Mesh: {mesh_pkg_name}.usx"
                        if ref_str not in res.texture_packages[sub_pkg_name].referenced_by:
                            res.texture_packages[sub_pkg_name].referenced_by.append(ref_str)
            except Exception:
                # Corrupted or unreadable mesh package; ignore non-fatal error
                pass

    def _resolve_disk_files(self, res: MapAnalysisResult):
        """Checks which packages physically exist on disk and tracks missing ones."""
        for name, pkg in res.all_packages().items():
            found_path = None
            if pkg.category == "StaticMeshes":
                found_path = self._find_client_file("StaticMeshes", f"{name}.usx")
            elif pkg.category in ("Textures", "SysTextures"):
                found_path = self._find_client_file("Textures", f"{name}.utx")
                if not found_path:
                    found_path = self._find_client_file("SysTextures", f"{name}.utx")
            elif pkg.category == "Sounds":
                found_path = self._find_client_file("Sounds", f"{name}.uax")
            elif pkg.category == "Animations":
                found_path = self._find_client_file("Animations", f"{name}.ukx")
            elif pkg.category == "Scripts":
                found_path = self._find_client_file("system", f"{name}.u")

            if found_path and found_path.exists():
                pkg.found = True
                pkg.file_path = found_path
                pkg.file_size = found_path.stat().st_size
            else:
                pkg.found = False
                res.missing_packages.append(name)

    def _find_client_file(self, subfolder: str, filename: str) -> Optional[Path]:
        if not self.client_root:
            return None
        target = self.client_root / subfolder / filename
        if target.exists():
            return target
        # Case-insensitive search on Windows if exact match fails
        parent = self.client_root / subfolder
        if parent.exists() and parent.is_dir():
            for f in parent.iterdir():
                if f.name.lower() == filename.lower():
                    return f
        return None
