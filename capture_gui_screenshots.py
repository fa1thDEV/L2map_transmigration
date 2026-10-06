#!/usr/bin/env python3
"""
Automated GUI Screenshot Generator
Captures high-resolution, pixel-perfect PNG screenshots of the UNR Tool GUI
in both English (EN) and Russian (RU) across all primary tabs with live data.
"""

import os
import sys
import time
import ctypes
from pathlib import Path
import tkinter as tk
from PIL import Image

# Ensure tool folder in path
TOOL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOL_DIR))

from gui import UNRToolApp
from i18n import i18n
from unr_analyzer import UNRAnalyzer
from terrain_inspector import MapInspector
from map_comparator import MapComparator


def capture_window(root: tk.Tk, output_path: Path):
    root.deiconify()
    root.lift()
    root.update()
    root.update_idletasks()
    time.sleep(0.08)

    hwnd = root.winfo_id()
    w = max(root.winfo_width(), 800)
    h = max(root.winfo_height(), 600)

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc_mem, hbm)

    # PW_RENDERFULLCONTENT = 2
    res = user32.PrintWindow(hwnd, hdc_mem, 2)
    if not res:
        # Fallback to PW_CLIENTONLY or 0
        user32.PrintWindow(hwnd, hdc_mem, 0)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ('biSize', ctypes.c_uint32), ('biWidth', ctypes.c_int32), ('biHeight', ctypes.c_int32),
            ('biPlanes', ctypes.c_uint16), ('biBitCount', ctypes.c_uint16), ('biCompression', ctypes.c_uint32),
            ('biSizeImage', ctypes.c_uint32), ('biXPelsPerMeter', ctypes.c_int32), ('biYPelsPerMeter', ctypes.c_int32),
            ('biClrUsed', ctypes.c_uint32), ('biClrImportant', ctypes.c_uint32)
        ]

    bih = BITMAPINFOHEADER()
    bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bih.biWidth = w
    bih.biHeight = -h
    bih.biPlanes = 1
    bih.biBitCount = 32

    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bih), 0)

    img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), 'PNG')

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    print(f"[OK] Saved screenshot: {output_path.name} ({w}x{h})")


def main():
    root = tk.Tk()
    app = UNRToolApp(root)
    root.geometry("1120x760+50+50")
    root.update()

    # Pre-populate with realistic test data
    test_map = TOOL_DIR / "Mapas de prueba" / "samurai_542" / "22_22.unr"
    client_dir = Path(r"E:\EndlessWar-proyecto\2-Juego")

    if test_map.exists():
        app.entry_unr.delete(0, "end")
        app.entry_unr.insert(0, str(test_map))
        out_folder = TOOL_DIR / "Mapas de prueba" / "samurai_542" / "Isolated_22_22"
        app.entry_output.delete(0, "end")
        app.entry_output.insert(0, str(out_folder))
        app.entry_iso_out.delete(0, "end")
        app.entry_iso_out.insert(0, str(out_folder))

        # Fill isolator metrics from actual completed run
        app.iso_vars["meshes"].set("494")
        app.iso_vars["textures"].set("118")
        app.iso_vars["downgraded"].set("3")
        app.iso_vars["size"].set("86.80 MB")
        app.text_iso_log.insert("end", "[SUCCESS] Single-Package Transmigration completed in 70.29 seconds!\n\n")
        app.text_iso_log.insert("end", "Generated bundle files:\n")
        app.text_iso_log.insert("end", "  * Maps/22_22.unr (25.86 MB) [Remapped to Map_22_22_S/T]\n")
        app.text_iso_log.insert("end", "  * StaticMeshes/Map_22_22_S.usx (48.97 MB) [494 Meshes]\n")
        app.text_iso_log.insert("end", "  * Textures/Map_22_22_T.utx (11.97 MB) [118 Textures]\n\n")
        app.text_iso_log.insert("end", "Replaced 76 external client packages with zero conflicts.\n")
        app.text_iso_log.insert("end", "Downgraded classes: Spotlight -> Light, AmbientSoundWObject -> AmbientSound, DynamicProjector -> Projector\n")

        # Analyze fast for census and tabs
        try:
            inspector = MapInspector.load_from_file(test_map)
            census = inspector.inspect()
            analyzer = UNRAnalyzer(client_root=client_dir if client_dir.exists() else None)
            res = analyzer.analyze_map(test_map, deep_mesh_scan=False)
            app.analysis_result = res
            app._update_ui_with_results(census)
        except Exception as e:
            print(f"[WARN] Quick analyze fallback: {e}")

    # Populate Diff Tab
    map_c6 = TOOL_DIR / "Mapas de prueba" / "c6_746" / "22_22.unr"
    if map_c6.exists() and test_map.exists():
        app.entry_diff_a.delete(0, "end")
        app.entry_diff_a.insert(0, str(map_c6))
        app.entry_diff_b.delete(0, "end")
        app.entry_diff_b.insert(0, str(test_map))
        try:
            comp = MapComparator(str(map_c6), str(test_map))
            diff = comp.compare()
            app.last_diff_result = diff
            d_size = (diff.map_b_size - diff.map_a_size) / (1024 * 1024)
            app.diff_vars["size"].set(f"{'+' if d_size >= 0 else ''}{d_size:.2f} MB")
            app.diff_vars["actors"].set(f"{diff.actors_b - diff.actors_a:+,}")
            app.diff_vars["meshes"].set(f"{len(diff.meshes_b) - len(diff.meshes_a):+,}")
            app.diff_vars["pkgs"].set(f"{len(diff.packages_b) - len(diff.packages_a):+,}")

            for item in app.tree_diff_actors.get_children():
                app.tree_diff_actors.delete(item)
            for cls in sorted(set(diff.class_counts_a.keys()).union(set(diff.class_counts_b.keys())))[:15]:
                ca = diff.class_counts_a.get(cls, 0)
                cb = diff.class_counts_b.get(cls, 0)
                delta = cb - ca
                d_str = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "=")
                app.tree_diff_actors.insert("", "end", values=(cls, ca, cb, d_str))

            app.list_diff_news.delete(0, "end")
            app.list_diff_news.insert("end", f"=== {len(diff.classes_added)} NEW CLASSES ===")
            for c in sorted(diff.classes_added)[:8]:
                app.list_diff_news.insert("end", f"  +{c}")
            app.list_diff_news.insert("end", "")
            app.list_diff_news.insert("end", f"=== {len(diff.packages_added)} NEW PACKAGES ===")
            for p in sorted(diff.packages_added)[:8]:
                app.list_diff_news.insert("end", f"  +{p}")
        except Exception as e:
            print(f"[WARN] Diff populate fallback: {e}")

    # Output directory
    out_dir = TOOL_DIR / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Artifact directory
    artifact_dir = Path(r"C:\Users\s7\.gemini\antigravity\brain\89c2e3f7-b73e-4d22-82b7-386085e31d17")

    tabs_to_capture = [
        (0, "01_summary_metrics"),
        (3, "02_terrain_actors"),
        (7, "03_map_diff"),
        (8, "04_autonomous_isolator"),
        (4, "05_utx_extractor"),
    ]

    for lang in ["en", "ru"]:
        i18n.set_language(lang)
        app._update_language_ui()
        root.update()

        for tab_idx, shot_name in tabs_to_capture:
            app.notebook.select(tab_idx)
            root.update()
            time.sleep(0.15)

            shot_file = out_dir / f"{shot_name}_{lang}.png"
            capture_window(root, shot_file)

            # Copy to artifacts directory
            if artifact_dir.exists():
                art_file = artifact_dir / f"{shot_name}_{lang}.png"
                try:
                    art_file.write_bytes(shot_file.read_bytes())
                except Exception as e:
                    print(f"Artifact copy error: {e}")

    root.destroy()
    print("\n[FINISHED] All interface screenshots generated in EN and RU!")


if __name__ == "__main__":
    main()
