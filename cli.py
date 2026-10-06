#!/usr/bin/env python3
"""
Command-Line Interface (CLI) for UNR Tool v1.5
Analyzes maps, resolves dependencies, extracts UTX textures, inspects terrain, and validates compatibility.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unr_analyzer import UNRAnalyzer
from asset_collector import AssetCollector
from manifest_generator import ManifestGenerator
from texture_optimizer import batch_resize_folder
from utx_extractor import UTXExtractor
from terrain_inspector import MapInspector
from engine_validator import ChronicleValidator
from map_comparator import MapComparator
from map_isolator import MapIsolator


DEFAULT_CLIENT = r"E:\EndlessWar-proyecto\2-Juego"


def main():
    parser = argparse.ArgumentParser(
        description="UNR Dependency & Downporting Toolkit v1.5 (Lineage 2 / Unreal Engine 2)"
    )
    parser.add_argument(
        "--unr",
        "-u",
        type=str,
        default="",
        help="Path to the .unr map file to analyze.",
    )
    parser.add_argument(
        "--client",
        "-c",
        type=str,
        default=DEFAULT_CLIENT if Path(DEFAULT_CLIENT).exists() else "",
        help=f"Path to the root game client folder (defaults to {DEFAULT_CLIENT}).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="",
        help="Destination folder for exported packages, manifests, and reports.",
    )
    parser.add_argument(
        "--no-deep",
        action="store_true",
        help="Disable deep scanning into .usx files for cascaded mesh textures.",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy all discovered package dependencies into the output directory.",
    )
    parser.add_argument(
        "--downscale",
        type=int,
        choices=[256, 512, 1024, 2048],
        default=None,
        help="Downscale image textures in the target folder to specified max dimension.",
    )
    parser.add_argument(
        "--downscale-folder",
        type=str,
        default="",
        help="Specific folder containing extracted textures to downscale.",
    )
    parser.add_argument(
        "--extract-utx",
        type=str,
        default="",
        help="Extract all textures from a .utx package to DDS and PNG files.",
    )
    parser.add_argument(
        "--check-compat",
        type=str,
        choices=["c4", "interlude", "h5", "classic"],
        default="",
        help="Validate map compatibility against a target chronicle.",
    )
    parser.add_argument(
        "--inspect-terrain",
        action="store_true",
        help="Print detailed TerrainInfo and StaticMesh actor census.",
    )
    parser.add_argument(
        "--compare",
        type=str,
        default="",
        help="Compare the target map (--unr) with another .unr map file across chronicles.",
    )
    parser.add_argument(
        "--isolate",
        action="store_true",
        help="Consolidate all map assets into a single USX and UTX file, remapping the UNR for plug-and-play transmigration.",
    )
    parser.add_argument(
        "--target-chronicle",
        type=str,
        choices=["c4", "interlude", "c6", "h5", "classic"],
        default="interlude",
        help="Target chronicle profile for isolation and downporting (default: interlude).",
    )

    args = parser.parse_args()

    # Mode 1: UTX Texture Extraction Standalone
    if args.extract_utx:
        utx_path = Path(args.extract_utx)
        if not utx_path.exists():
            print(f"[ERROR] UTX package not found: {utx_path}")
            sys.exit(1)
        out_folder = Path(args.output) if args.output else utx_path.parent / f"Extracted_{utx_path.stem}"
        print(f"\n[EXTRACT UTX] Reading {utx_path.name}...")
        extractor = UTXExtractor(utx_path)
        textures = extractor.list_textures()
        print(f"  -> Found {len(textures)} texture exports.")
        saved = extractor.export_all_to_folder(out_folder)
        print(f"  -> Successfully extracted {len(saved)} files to {out_folder}\n")
        return

    if not args.unr:
        parser.print_help()
        sys.exit(0)

    unr_path = Path(args.unr)
    if not unr_path.exists():
        print(f"[ERROR] UNR file not found: {unr_path}")
        sys.exit(1)

    client_path = Path(args.client) if args.client else None

    # Mode 2: Cross-Chronicle Map Comparison
    if args.compare:
        map_b_path = Path(args.compare)
        if not map_b_path.exists():
            print(f"[ERROR] Map to compare not found: {map_b_path}")
            sys.exit(1)
        print(f"\n[MAP COMPARISON] Comparing {unr_path.name} vs {map_b_path.name}...")
        comparator = MapComparator(unr_path, map_b_path)
        diff = comparator.compare()
        report_md = comparator.generate_markdown_report(diff)

        print(f"  -> {diff.map_a_name}: {diff.actors_a:,} actors, {len(diff.packages_a)} pkgs, {len(diff.meshes_a)} meshes")
        print(f"  -> {diff.map_b_name}: {diff.actors_b:,} actors, {len(diff.packages_b)} pkgs, {len(diff.meshes_b)} meshes")
        print(f"  -> Actor Delta:    {diff.actors_b - diff.actors_a:+,} actors")
        print(f"  -> Added Packages: {len(diff.packages_added)}")
        print(f"  -> New Classes:    {len(diff.classes_added)} ({', '.join(sorted(diff.classes_added)) if diff.classes_added else 'None'})")

        out_report_dir = Path(args.output) if args.output else unr_path.parent
        out_report_dir.mkdir(parents=True, exist_ok=True)
        report_file = out_report_dir / f"diff_{unr_path.stem}_vs_{map_b_path.stem}.md"
        report_file.write_text(report_md, encoding="utf-8")
        print(f"  -> Saved full diff report to: {report_file}\n")
        return

    # Mode 3: Single-Package Map Isolation (1 Archivo por Clase)
    if args.isolate:
        if not client_path:
            print("[ERROR] Game client path required for isolation. Specify --client <path>.")
            sys.exit(1)
        out_iso_dir = Path(args.output) if args.output else unr_path.parent / f"Isolated_{unr_path.stem}"
        print(f"\n=======================================================")
        print(f" UNR Single-Package Transmigration Pipeline")
        print(f" Source Map:       {unr_path.name}")
        print(f" Client Root:      {client_path}")
        print(f" Target Chronicle: {args.target_chronicle.upper()}")
        print(f" Output Folder:    {out_iso_dir}")
        print(f"=======================================================\n")

        isolator = MapIsolator(client_root=client_path)
        res = isolator.isolate_map(
            unr_path=unr_path,
            output_dir=out_iso_dir,
            target_chronicle=args.target_chronicle,
        )
        print(f"[SUCCESS] Isolated deployment bundle created in {res.output_dir}:")
        print(f"  * Maps/{res.remapped_unr_path.name}")
        print(f"  * StaticMeshes/{res.consolidated_usx_path.name}")
        print(f"  * Textures/{res.consolidated_utx_path.name}")
        return

    out_dir = Path(args.output) if args.output else unr_path.parent / f"Export_{unr_path.stem}"

    print(f"\n=======================================================")
    print(f" UNR Dependency & Downporting Toolkit v1.6")
    print(f" Target Map:  {unr_path.name}")
    print(f" Client Root: {client_path if client_path else 'Not specified'}")
    print(f" Output Dir:  {out_dir}")
    print(f"=======================================================\n")

    # 1. Analyze map
    print("[1/5] Analyzing map structure and package headers...")
    analyzer = UNRAnalyzer(client_root=client_path)
    res = analyzer.analyze_map(unr_path, deep_mesh_scan=not args.no_deep)

    print(f"  -> Version: UE2 v{res.unreal_version} (Licensee {res.licensee_mode})")
    print(f"  -> StaticMesh Packages: {len(res.static_mesh_packages)}")
    print(f"  -> Texture Packages:    {len(res.texture_packages)}")
    print(f"  -> Sound Packages:      {len(res.sound_packages)}")
    print(f"  -> 3D Meshes Referenced: {len(res.static_meshes_used)}")
    print(f"  -> Textures/Shaders:    {len(res.textures_used) + len(res.shaders_used)}")

    # 2. Inspect Terrain & Placements if requested
    if args.inspect_terrain:
        print("\n[2/5] Inspecting terrain and actor census...")
        insp = MapInspector.load_from_file(unr_path)
        census = insp.inspect()
        print(f"  -> Total Actors Placed: {census.total_actors}")
        if census.terrain:
            print(f"  -> Heightmap: {census.terrain.heightmap_texture}")
            print(f"  -> Scale:     {census.terrain.terrain_scale}")
        print(f"  -> Top Placed Static Meshes:")
        for mesh, cnt in list(census.static_mesh_usage.items())[:5]:
            print(f"     * {mesh}: {cnt} instances")
    else:
        print("\n[2/5] Actor census skipped (pass --inspect-terrain to inspect).")

    # 3. Chronicle Compatibility Validation
    if args.check_compat:
        print(f"\n[3/5] Validating compatibility against {args.check_compat.upper()}...")
        validator = ChronicleValidator(target_chronicle=args.check_compat)
        rep = validator.validate_map(unr_path)
        if rep.is_compatible:
            print(f"  -> Map is COMPATIBLE with {args.check_compat.upper()}!")
        else:
            print(f"  -> Map has {rep.critical_count()} CRITICAL compatibility issues:")
            for issue in rep.issues:
                print(f"     [{issue.severity}] {issue.category} - {issue.item_name}: {issue.message}")
                print(f"       Solution: {issue.recommendation}")
    else:
        print("\n[3/5] Chronicle validation skipped (pass --check-compat <c4|interlude|h5>).")

    # 4. Export / Copy packages if requested
    if args.copy:
        print(f"\n[4/5] Isolating and copying packages to {out_dir}...")
        collector = AssetCollector(target_directory=out_dir)
        summary = collector.export_dependencies(res)
        print(f"  -> Copied {len(summary.copied_files)} files ({summary.total_bytes_copied / (1024*1024):.2f} MB)")
        if summary.missing_files:
            print(f"  -> WARNING: {len(summary.missing_files)} packages missing in client:")
            for m in summary.missing_files[:5]:
                print(f"     - {m}")
            if len(summary.missing_files) > 5:
                print(f"     - ...and {len(summary.missing_files) - 5} more.")
    else:
        print("\n[4/5] Package copy skipped (pass --copy to isolate files).")

    # 5. Generate Reports
    print(f"\n[5/5] Generating reports...")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_gen = ManifestGenerator(res)

    json_path = manifest_gen.save_json(out_dir / f"{unr_path.stem}_manifest.json")
    html_path = manifest_gen.save_html(out_dir / f"{unr_path.stem}_report.html")
    md_path = manifest_gen.save_markdown(out_dir / f"{unr_path.stem}_report.md")

    print(f"  -> JSON Manifest: {json_path}")
    print(f"  -> HTML Report:   {html_path}")
    print(f"  -> Markdown:      {md_path}")

    # Downscale textures if requested
    if args.downscale:
        target_tex_dir = Path(args.downscale_folder) if args.downscale_folder else out_dir / "Textures"
        if target_tex_dir.exists():
            print(f"\nDownscaling textures in {target_tex_dir} to max {args.downscale}x{args.downscale}...")
            records = batch_resize_folder(
                src_folder=target_tex_dir,
                dst_folder=out_dir / f"Textures_{args.downscale}",
                max_dimension=args.downscale,
            )
            success_count = sum(1 for r in records if r.success)
            print(f"  -> Processed {success_count} / {len(records)} images.")

    print("\n[DONE] Process completed successfully!\n")


if __name__ == "__main__":
    main()
