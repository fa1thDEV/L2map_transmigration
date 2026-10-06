#!/usr/bin/env python3
"""
Asset Collector for UNR Tool
Copies and organizes map dependencies into a clean directory structure.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional

from unr_analyzer import MapAnalysisResult, ResolvedPackage


@dataclass
class ExportSummary:
    target_dir: Path
    copied_files: List[Tuple[str, Path, int]] = field(default_factory=list)  # (category, dst_path, size)
    total_bytes_copied: int = 0
    missing_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class AssetCollector:
    """Collects and copies all assets referenced by a map to an isolated destination folder."""

    def __init__(self, target_directory: Path | str):
        self.target_dir = Path(target_directory)

    def export_dependencies(
        self,
        analysis: MapAnalysisResult,
        include_map: bool = True,
        include_sounds: bool = True,
        overwrite: bool = True,
    ) -> ExportSummary:
        self.target_dir.mkdir(parents=True, exist_ok=True)
        summary = ExportSummary(target_dir=self.target_dir)

        # 1. Copy Map file
        if include_map and analysis.map_path.exists():
            maps_folder = self.target_dir / "Maps"
            maps_folder.mkdir(exist_ok=True)
            dst_map = maps_folder / analysis.map_path.name
            try:
                if overwrite or not dst_map.exists():
                    shutil.copy2(analysis.map_path, dst_map)
                size = dst_map.stat().st_size
                summary.copied_files.append(("Maps", dst_map, size))
                summary.total_bytes_copied += size
            except Exception as e:
                summary.errors.append(f"Failed to copy map {analysis.map_path.name}: {e}")

        # 2. Copy Packages by Category
        for name, pkg in analysis.all_packages().items():
            if not include_sounds and pkg.category == "Sounds":
                continue
            if pkg.category == "Scripts":
                # System .u files are engine-specific, do not copy by default unless needed
                continue

            if not pkg.found or not pkg.file_path or not pkg.file_path.exists():
                summary.missing_files.append(f"{pkg.category}/{name}{pkg.expected_extension}")
                continue

            cat_folder = self.target_dir / pkg.category
            cat_folder.mkdir(exist_ok=True)
            dst_file = cat_folder / pkg.file_path.name

            try:
                if overwrite or not dst_file.exists():
                    shutil.copy2(pkg.file_path, dst_file)
                size = dst_file.stat().st_size
                summary.copied_files.append((pkg.category, dst_file, size))
                summary.total_bytes_copied += size
            except Exception as e:
                summary.errors.append(f"Failed to copy {pkg.file_path.name}: {e}")

        return summary
