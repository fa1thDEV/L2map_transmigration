#!/usr/bin/env python3
"""
Map Comparator & Evolution Differ for UNR Tool
Performs deep side-by-side comparison between two .unr maps across chronicles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ue2_package import UE2Package
from terrain_inspector import MapInspector, MapCensus


@dataclass
class MapDiffResult:
    map_a_name: str
    map_b_name: str
    map_a_size: int
    map_b_size: int

    ue_ver_a: int
    ue_ver_b: int
    licensee_a: int
    licensee_b: int

    actors_a: int
    actors_b: int

    packages_a: Set[str] = field(default_factory=set)
    packages_b: Set[str] = field(default_factory=set)
    packages_added: Set[str] = field(default_factory=set)
    packages_removed: Set[str] = field(default_factory=set)
    packages_common: Set[str] = field(default_factory=set)

    classes_a: Set[str] = field(default_factory=set)
    classes_b: Set[str] = field(default_factory=set)
    classes_added: Set[str] = field(default_factory=set)
    classes_removed: Set[str] = field(default_factory=set)

    class_counts_a: Dict[str, int] = field(default_factory=dict)
    class_counts_b: Dict[str, int] = field(default_factory=dict)

    meshes_a: Dict[str, int] = field(default_factory=dict)
    meshes_b: Dict[str, int] = field(default_factory=dict)
    meshes_added: Set[str] = field(default_factory=set)
    meshes_removed: Set[str] = field(default_factory=set)


class MapComparator:
    """Compares two .unr map packages across chronicles."""

    def __init__(self, map_a_path: Path | str, map_b_path: Path | str):
        self.path_a = Path(map_a_path)
        self.path_b = Path(map_b_path)

    def compare(self) -> MapDiffResult:
        pkg_a = UE2Package.load_from_file(self.path_a)
        pkg_b = UE2Package.load_from_file(self.path_b)

        insp_a = MapInspector(pkg_a)
        insp_b = MapInspector(pkg_b)

        census_a = insp_a.inspect()
        census_b = insp_b.inspect()

        pkgs_a = pkg_a.get_imported_packages()
        pkgs_b = pkg_b.get_imported_packages()

        classes_a = {imp.object_name for imp in pkg_a.imports if imp.class_name.lower() == "class"}
        classes_b = {imp.object_name for imp in pkg_b.imports if imp.class_name.lower() == "class"}

        meshes_a_set = set(census_a.static_mesh_usage.keys())
        meshes_b_set = set(census_b.static_mesh_usage.keys())

        return MapDiffResult(
            map_a_name=self.path_a.name,
            map_b_name=self.path_b.name,
            map_a_size=self.path_a.stat().st_size,
            map_b_size=self.path_b.stat().st_size,
            ue_ver_a=pkg_a.summary.file_version,
            ue_ver_b=pkg_b.summary.file_version,
            licensee_a=pkg_a.summary.licensee_mode,
            licensee_b=pkg_b.summary.licensee_mode,
            actors_a=census_a.total_actors,
            actors_b=census_b.total_actors,
            packages_a=pkgs_a,
            packages_b=pkgs_b,
            packages_added=pkgs_b - pkgs_a,
            packages_removed=pkgs_a - pkgs_b,
            packages_common=pkgs_a.intersection(pkgs_b),
            classes_a=classes_a,
            classes_b=classes_b,
            classes_added=classes_b - classes_a,
            classes_removed=classes_a - classes_b,
            class_counts_a=census_a.actor_class_counts,
            class_counts_b=census_b.actor_class_counts,
            meshes_a=census_a.static_mesh_usage,
            meshes_b=census_b.static_mesh_usage,
            meshes_added=meshes_b_set - meshes_a_set,
            meshes_removed=meshes_a_set - meshes_b_set,
        )

    def generate_markdown_report(self, diff: MapDiffResult) -> str:
        lines = [
            f"# Cross-Chronicle Map Comparison: {diff.map_a_name} vs {diff.map_b_name}",
            "",
            "## 1. Core Engine & File Metrics",
            "| Metric | Map A (Baseline) | Map B (Target) | Evolution / Delta |",
            "| :--- | :--- | :--- | :--- |",
            f"| **File Name** | `{diff.map_a_name}` | `{diff.map_b_name}` | - |",
            f"| **File Size** | {diff.map_a_size / (1024*1024):.2f} MB | {diff.map_b_size / (1024*1024):.2f} MB | +{(diff.map_b_size - diff.map_a_size) / (1024*1024):.2f} MB |",
            f"| **Unreal Engine Version** | Version {diff.ue_ver_a} (Lic {diff.licensee_a}) | Version {diff.ue_ver_b} (Lic {diff.licensee_b}) | {'Version Bump' if diff.ue_ver_b > diff.ue_ver_a else 'Same'} |",
            f"| **Total Placed Actors** | {diff.actors_a:,} | {diff.actors_b:,} | {diff.actors_b - diff.actors_a:+,} actors |",
            f"| **Imported Packages** | {len(diff.packages_a)} | {len(diff.packages_b)} | {len(diff.packages_b) - len(diff.packages_a):+} packages |",
            f"| **Unique 3D Meshes** | {len(diff.meshes_a)} | {len(diff.meshes_b)} | {len(diff.meshes_b) - len(diff.meshes_a):+} meshes |",
            "",
            "## 2. Actor Class Count Breakdown",
            "| Actor Class | Map A Count | Map B Count | Change |",
            "| :--- | :---: | :---: | :--- |",
        ]

        all_classes = sorted(set(diff.class_counts_a.keys()).union(set(diff.class_counts_b.keys())))
        for cls in all_classes:
            ca = diff.class_counts_a.get(cls, 0)
            cb = diff.class_counts_b.get(cls, 0)
            delta = cb - ca
            delta_str = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "=")
            lines.append(f"| `{cls}` | {ca:,} | {cb:,} | **{delta_str}** |")

        lines.extend([
            "",
            f"## 3. New Engine Classes Added in Map B ({len(diff.classes_added)})",
            "These classes were introduced in the newer chronicle and will cause crashes if imported into an engine that lacks them:",
        ])
        for c in sorted(diff.classes_added):
            lines.append(f"- `+{c}`")

        lines.extend([
            "",
            f"## 4. Package Additions in Map B ({len(diff.packages_added)})",
        ])
        for p in sorted(diff.packages_added):
            lines.append(f"- `+{p}`")

        lines.extend([
            "",
            f"## 5. Top 15 Most Placed 3D Models in Map B",
            "| Static Mesh Reference | Placement Count | Present in Map A? |",
            "| :--- | :---: | :---: |",
        ])
        sorted_meshes_b = sorted(diff.meshes_b.items(), key=lambda x: x[1], reverse=True)
        for m, count in sorted_meshes_b[:15]:
            in_a = "Yes" if m in diff.meshes_a else "**NEW**"
            lines.append(f"| `{m}` | {count:,} | {in_a} |")

        return "\n".join(lines) + "\n"
