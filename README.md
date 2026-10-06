# UNR Dependency & Downporting Toolkit v1.7

A complete, standalone Python toolkit to inspect, isolate, extract, adapt, and compare Lineage 2 Unreal Engine 2 map sectors (`.unr`), their 3D static meshes (`.usx`), and texture dependencies (`.utx`).

---

## What's New in v1.7

1. **Single-Package Map Transmigration & Isolation (`map_isolator.py`, `unr_remapper.py`, `usx_consolidator.py`, `utx_consolidator.py`)**:
   - **1 Archivo por Clase**: Consolida automáticamente todas las mallas en `Map_{SECTOR}_S.usx` y todas las texturas/heightmaps en `Map_{SECTOR}_T.utx`.
   - **Remapeo de Punteros en `.unr`**: Redirige todas las referencias del mapa hacia los dos paquetes maestros únicos.
   - **Cero Colisiones**: Permite instalar cualquier mapa en cualquier cliente sin sobreescribir paquetes retail (`Goddard_S`, `Aden_S`, etc.) ni entrar en conflicto de dependencias.
   - **Parcheo de Crónica y Downgrade Automático**: Convierte cabeceras de versión (`v123`, `lic 28/37`) y degrada clases modernas incompatibles (`Spotlight` $\rightarrow$ `Light`, `AmbientSoundWObject` $\rightarrow$ `AmbientSound`, `DynamicProjector` $\rightarrow$ `Projector`).

2. **Pestaña GUI Dedicada: 📦 Empaquetador Autónomo (1/Clase)**:
   - Permite seleccionar la crónica de destino y generar el bundle de 3 archivos en 1 solo clic.

3. **Cross-Chronicle Map Comparator & Differ (`map_comparator.py`)**:
   - Compara mapas `.unr` frente a frente con cálculo automático de deltas y reporte en Markdown.

4. **Native UTX Texture Extractor (`utx_extractor.py`)**:
   - Extrae texturas DXT1/3/5, RGBA8, G16 a DDS y PNG nativos sin herramientas externas.

5. **Terrain & Actor Placement Census (`terrain_inspector.py`)**:
   - Extrae el heightmap, escala de terreno y conteo exacto de actores y mallas 3D.

---

## File Structure

```
UNR_tool_v1/
├── l2_crypt.py           # Decryption/encryption for Lineage 2 package headers
├── ue2_package.py        # Low-level UE2 package parser and serializer
├── unr_analyzer.py       # High-level map dependency analyzer
├── utx_extractor.py      # Native UTX texture extractor (DDS & PNG)
├── terrain_inspector.py  # TerrainInfo & StaticMesh placement inspector
├── engine_validator.py   # Cross-chronicle compatibility validator (C4 / Interlude / H5 / Classic)
├── map_comparator.py     # Cross-chronicle map differ and delta analyzer
├── unr_remapper.py       # UNR import table remapper & chronicle downgrader
├── utx_consolidator.py   # Consolidates all map textures into 1 master Map_{NAME}_T.utx
├── usx_consolidator.py   # Consolidates all map static meshes into 1 master Map_{NAME}_S.usx
├── map_isolator.py       # Master orchestrator for Single-Package Map Transmigration
├── asset_collector.py    # Asset copier and folder organizer
├── texture_optimizer.py  # Image batch resizer and Power-of-Two clamping
├── manifest_generator.py # JSON, HTML, and Markdown report generators
├── cli.py                # Command-Line Interface entry point (v1.7)
├── gui.py                # Tkinter Graphical User Interface (v1.7)
├── run_gui.bat           # 1-click Windows launcher for GUI
├── run_cli_example.bat   # Example CLI execution batch file
├── COMPARACION_C6_VS_OUR.md       # Comparative study: C6 vs Classic
├── COMPARACION_OUR_VS_SAMURAI.md  # Comparative study: Classic vs Modern Samurai
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
