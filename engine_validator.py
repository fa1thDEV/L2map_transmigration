#!/usr/bin/env python3
"""
Engine Compatibility & Cross-Chronicle Validator for UNR Tool
Validates map classes and structures against target chronicles (C4, Interlude, High Five, Classic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ue2_package import UE2Package


@dataclass
class CompatibilityIssue:
    severity: str  # 'CRITICAL', 'WARNING', 'INFO'
    category: str
    item_name: str
    message: str
    recommendation: str


@dataclass
class ValidationReport:
    map_name: str
    target_chronicle: str
    is_compatible: bool
    issues: List[CompatibilityIssue] = field(default_factory=list)

    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")


class ChronicleValidator:
    """Validates whether a map's classes and features can run in older chronicles."""

    # Standard classes available in C4 / Interlude Unreal Engine 2.0 (UE2 Build 118-123)
    RETAIL_C4_CLASSES: Set[str] = {
        "actor", "camera", "brush", "polys", "model", "staticmesh", "staticmeshactor",
        "staticmeshinstance", "terraininfo", "terrainsector", "levelinfo", "levelsummary",
        "zoneinfo", "skyzoneinfo", "watervolume", "physicsvolume", "playerstart", "light",
        "sunlight", "ambientlight", "ambientsound", "ambientvolume", "blockingvolume",
        "texture", "shader", "palette", "material", "finalblend", "combiner", "colormodifier",
        "texmodifier", "texpanner", "texrotator", "texscaler", "texoscillator", "constantcolor",
        "fadecolor", "cubemap", "fractaltexture", "firetexture", "icetexture", "watertexture",
        "waveformatloader", "sound", "package", "class", "level"
    }

    # Classes added in newer engines (Gracia, Freya, H5, GoD, Classic)
    NEWER_ENGINE_CLASSES: Dict[str, Tuple[str, str]] = {
        "nmovablesunlight": (
            "Custom Lineage 2 dynamic sunlight class",
            "Replace with standard 'Light' or 'SunLight' before importing to C4/Interlude."
        ),
        "nmoon": (
            "Custom dynamic moon celestial body actor",
            "Replace with classic SkyZoneInfo mesh or static billboard."
        ),
        "nsun": (
            "Custom dynamic sun actor with modern corona flare",
            "Replace with classic Light/Corona actor."
        ),
        "postprocessvolume": (
            "Modern post-processing volume (HDR, Bloom, ToneMapping)",
            "Delete or replace with standard ZoneInfo in C4."
        ),
        "decolayer": (
            "Advanced grass/foliage decorator layer",
            "C4 terrain decorators are limited; simplify or remove DecoLayers."
        ),
    }

    CHRONICLE_MAX_VERSIONS: Dict[str, int] = {
        "c4": 121,
        "interlude": 123,
        "h5": 129,
        "classic": 133,
    }

    def __init__(self, target_chronicle: str = "c4"):
        self.target = target_chronicle.lower()

    def validate_map(self, map_path: Path | str) -> ValidationReport:
        pkg = UE2Package.load_from_file(map_path)
        report = ValidationReport(
            map_name=pkg.filename,
            target_chronicle=self.target.upper(),
            is_compatible=True,
        )

        # 1. Check Package Version
        max_ver = self.CHRONICLE_MAX_VERSIONS.get(self.target, 121)
        if pkg.summary.file_version > max_ver:
            report.issues.append(CompatibilityIssue(
                severity="CRITICAL",
                category="Package Version",
                item_name=f"UE2 Version {pkg.summary.file_version}",
                message=f"File version {pkg.summary.file_version} exceeds {self.target.upper()} maximum supported version ({max_ver}).",
                recommendation=f"Must be exported to .T3D and re-built/saved in the {self.target.upper()} UnrealEd editor."
            ))
            report.is_compatible = False

        # 2. Check Imported Classes
        for imp in pkg.imports:
            cls_lower = imp.class_name.lower()
            if cls_lower in self.NEWER_ENGINE_CLASSES:
                desc, fix = self.NEWER_ENGINE_CLASSES[cls_lower]
                report.issues.append(CompatibilityIssue(
                    severity="CRITICAL" if self.target in ("c4", "interlude") else "WARNING",
                    category="Missing Class",
                    item_name=imp.object_name,
                    message=f"Actor class '{imp.object_name}' ({desc}) does not exist in {self.target.upper()}.",
                    recommendation=fix
                ))
                if self.target in ("c4", "interlude"):
                    report.is_compatible = False

        # 3. Check Texture Sizes (if client available or referenced)
        for imp in pkg.imports:
            if imp.class_name.lower() == "texture":
                # Check naming hints
                tname = imp.object_name.lower()
                if "2048" in tname:
                    report.issues.append(CompatibilityIssue(
                        severity="WARNING",
                        category="Texture Resolution",
                        item_name=imp.full_path,
                        message=f"Texture '{imp.object_name}' suggests 2048x2048 resolution, which can exhaust memory in {self.target.upper()}.",
                        recommendation="Downscale texture to 1024x1024 or 512x512 using UNR Tool texture optimizer."
                    ))

        return report
