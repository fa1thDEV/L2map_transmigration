# UNR Dependency & Downporting Toolkit v1.5

A complete, standalone Python toolkit to inspect, isolate, extract, and adapt Lineage 2 Unreal Engine 2 map sectors (`.unr`), their 3D static meshes (`.usx`), and texture dependencies (`.utx`).

---

## What's New in v1.5

1. **Native UTX Texture Extractor (`utx_extractor.py`)**:
   - Parses `.utx` texture packages directly (with L2 decryption).
   - Extracts embedded mipmaps and compressed DXT1, DXT3, DXT5, RGBA8, and G16 textures.
   - Automatically generates valid DirectX `.dds` files and standard `.png` images without needing external closed-source tools.

2. **Terrain & Actor Placement Census (`terrain_inspector.py`)**:
   - Parses `TerrainInfo` actors to extract heightmap references and terrain scale (X, Y, Z).
   - Counts exact placements of every 3D model on the map (e.g. `Glacia_base`: 2 instances).
   - Breaks down actor counts by class (`StaticMeshActor`, `Camera`, `Brush`, `TerrainSector`, etc.).

3. **Engine Compatibility & Chronicle Validator (`engine_validator.py`)**:
   - Validates map structure and actor classes against target chronicles: **C4 (Scions of Destiny)**, **Interlude (The Chaotic Throne)**, and **High Five**.
   - Flags missing engine classes (e.g. `NMovableSunLight`, `NMoon`, `PostProcessVolume`) that will crash older game clients.
   - Provides concrete recommendations to fix compatibility issues.

4. **Default Client Auto-Detection**:
   - Automatically detects the unpacked client in `E:\EndlessWar-proyecto\2-Juego`.
   - Inspects unpacked DLLs (`Engine.dll`, `Core.dll`, `NWindow.dll`) for supported engine classes and structures.

---

## File Structure

```
UNR_tool_v1/
├── l2_crypt.py           # Decryption/encryption for Lineage 2 package headers
├── ue2_package.py        # Low-level UE2 package file parser
├── unr_analyzer.py       # High-level map dependency analyzer
├── utx_extractor.py      # Native UTX texture extractor (DDS & PNG)
├── terrain_inspector.py  # TerrainInfo & StaticMesh placement inspector
├── engine_validator.py   # Cross-chronicle compatibility validator (C4 / Interlude / H5)
├── asset_collector.py    # Asset copier and folder organizer
├── texture_optimizer.py  # Image batch resizer and Power-of-Two clamping
├── manifest_generator.py # JSON, HTML, and Markdown report generators
├── cli.py                # Command-Line Interface entry point
├── gui.py                # Tkinter Graphical User Interface (v1.5)
├── run_gui.bat           # 1-click Windows launcher for GUI
├── run_cli_example.bat   # Example CLI execution batch file
└── README.md             # This documentation
```

---

## GUI Usage (`run_gui.bat`)

Double-click `run_gui.bat` to launch the dark-themed desktop application:

1. **Mapa (.UNR):** Browse and select the map you want to port.
2. **Cliente L2 Root:** Pre-filled with `E:\EndlessWar-proyecto\2-Juego`.
3. **Carpeta Destino:** Where isolated files and reports will be saved.
4. **Tabs Available:**
   - **📊 Resumen y Métricas:** Overall sizes, engine versions, and package statistics.
   - **📦 Paquetes Requeridos:** Complete list of `.usx`, `.utx`, and `.uax` packages with found/missing status.
   - **🎨 Mallas y Texturas:** Exhaustive list of all 3D models and textures referenced.
   - **🏔️ Terreno & Actores:** Heightmap texture reference, terrain scaling, and instance counts per 3D mesh.
   - **🖼️ Extractor UTX:** Inspect any `.utx` package, view internal textures with dimensions and formats, and extract them to `.dds` / `.png` in 1 click.
   - **⚡ Redimensionar Texturas:** Batch downscaler for textures (512x512, 1024x1024) enforcing power-of-two limits.
   - **🛡️ Validador de Crónica:** Choose target chronicle (C4, Interlude, H5) to check for incompatible actors or versions.

---

## CLI Usage (`cli.py`)

```bash
# 1. Analyze map, check C4 compatibility, and inspect terrain
python cli.py --unr "E:\EndlessWar-proyecto\2-Juego\Maps\11_21.unr" --check-compat c4 --inspect-terrain

# 2. Isolate and copy all map dependencies to an export folder
python cli.py --unr "E:\EndlessWar-proyecto\2-Juego\Maps\11_21.unr" --copy --output "output_11_21"

# 3. Extract all textures from a UTX package directly
python cli.py --extract-utx "E:\EndlessWar-proyecto\2-Juego\Textures\T_texture.utx" --output "extracted_textures"

# 4. Downscale textures to 512x512
python cli.py --downscale 512 --downscale-folder "extracted_textures" --output "downscaled_512"
```

---

## Requirements

- Python 3.10+
- `Pillow` (`pip install Pillow`)
- Standard Windows GUI (`tkinter` included with Python)
