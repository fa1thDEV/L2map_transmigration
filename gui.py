#!/usr/bin/env python3
"""
Graphical User Interface (GUI) for UNR Tool v1.5
Modern Tkinter desktop application for analyzing, isolating, extracting, and downporting Lineage 2 maps.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from unr_analyzer import UNRAnalyzer, MapAnalysisResult
from asset_collector import AssetCollector
from manifest_generator import ManifestGenerator, format_bytes
from texture_optimizer import batch_resize_folder
from utx_extractor import UTXExtractor
from terrain_inspector import MapInspector, MapCensus
from engine_validator import ChronicleValidator


DEFAULT_CLIENT_DIR = r"E:\EndlessWar-proyecto\2-Juego"


class UNRToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("UNR Dependency & Downporting Toolkit v1.5")
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)

        # State
        self.analysis_result: MapAnalysisResult | None = None
        self.last_html_report: Path | None = None
        self.active_utx_extractor: UTXExtractor | None = None

        self._setup_styles()
        self._create_layout()

    def _setup_styles(self):
        self.bg_color = "#111827"       # Slate 900
        self.panel_bg = "#1f2937"       # Slate 800
        self.card_bg = "#374151"        # Slate 700
        self.text_color = "#f9fafb"     # White / Light gray
        self.text_muted = "#9ca3af"     # Muted gray
        self.accent_color = "#38bdf8"   # Sky blue
        self.success_color = "#22c55e"  # Green
        self.warning_color = "#f59e0b"  # Amber
        self.danger_color = "#ef4444"   # Red

        self.root.configure(bg=self.bg_color)

        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 9))
        style.configure("TFrame", background=self.bg_color)
        style.configure("Card.TFrame", background=self.panel_bg, relief="flat")
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        style.configure("Card.TLabel", background=self.panel_bg, foreground=self.text_color)
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground=self.accent_color)
        style.configure("MetricVal.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.text_color, background=self.card_bg)
        style.configure("MetricLbl.TLabel", font=("Segoe UI", 8), foreground=self.text_muted, background=self.card_bg)

        # Notebook tabs
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.panel_bg, foreground=self.text_muted, padding=[12, 6], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", self.card_bg)], foreground=[("selected", self.accent_color)])

        # Treeview
        style.configure("Treeview", background="#182234", foreground=self.text_color, fieldbackground="#182234", rowheight=24)
        style.configure("Treeview.Heading", background=self.panel_bg, foreground=self.text_color, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2563eb")], foreground=[("selected", "#ffffff")])

        # Buttons
        style.configure("Primary.TButton", background="#0284c7", foreground="#ffffff", font=("Segoe UI", 9, "bold"), padding=[10, 5])
        style.map("Primary.TButton", background=[("active", "#0369a1")])
        style.configure("Action.TButton", background="#10b981", foreground="#ffffff", font=("Segoe UI", 9, "bold"), padding=[10, 5])
        style.map("Action.TButton", background=[("active", "#059669")])

    def _create_layout(self):
        # Header banner
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="UNR Dependency & Downporting Toolkit", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="Lineage 2 / Unreal Engine 2 & Unpacked DLLs Ready", foreground=self.text_muted).pack(side="left", padx=10, pady=(4, 0))

        # Main Input Control Panel
        control_panel = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        control_panel.pack(fill="x", padx=12, pady=6)

        # UNR File selector
        r1 = ttk.Frame(control_panel, style="Card.TFrame")
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Mapa (.UNR):", style="Card.TLabel", width=16).pack(side="left")
        self.entry_unr = tk.Entry(r1, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_unr.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r1, text="Examinar...", command=self._browse_unr).pack(side="right")

        # Client Root selector
        r2 = ttk.Frame(control_panel, style="Card.TFrame")
        r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Cliente L2 Root:", style="Card.TLabel", width=16).pack(side="left")
        self.entry_client = tk.Entry(r2, bg="#111827", fg=self.text_color, insertbackground="white")
        if os.path.exists(DEFAULT_CLIENT_DIR):
            self.entry_client.insert(0, DEFAULT_CLIENT_DIR)
        self.entry_client.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r2, text="Examinar...", command=self._browse_client).pack(side="right")

        # Output Folder selector
        r3 = ttk.Frame(control_panel, style="Card.TFrame")
        r3.pack(fill="x", pady=2)
        ttk.Label(r3, text="Carpeta Destino:", style="Card.TLabel", width=16).pack(side="left")
        self.entry_output = tk.Entry(r3, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_output.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r3, text="Examinar...", command=self._browse_output).pack(side="right")

        # Options & Action Buttons Bar
        action_bar = ttk.Frame(control_panel, style="Card.TFrame")
        action_bar.pack(fill="x", pady=(8, 0))

        self.var_deep_scan = tk.BooleanVar(value=True)
        cb_deep = tk.Checkbutton(
            action_bar, text="Escaneo Profundo (.usx -> texturas)",
            variable=self.var_deep_scan, bg=self.panel_bg, fg=self.text_color,
            selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.text_color
        )
        cb_deep.pack(side="left", padx=5)

        self.btn_analyze = ttk.Button(action_bar, text="🔍 Analizar Mapa", style="Primary.TButton", command=self._on_analyze)
        self.btn_analyze.pack(side="left", padx=8)

        self.btn_export = ttk.Button(action_bar, text="📦 Exportar Dependencias", style="Action.TButton", command=self._on_export)
        self.btn_export.pack(side="left", padx=5)

        self.btn_open_html = ttk.Button(action_bar, text="🌐 Abrir Reporte HTML", command=self._open_html_report)
        self.btn_open_html.pack(side="right", padx=5)

        self.btn_open_folder = ttk.Button(action_bar, text="📁 Abrir Carpeta", command=self._open_output_folder)
        self.btn_open_folder.pack(side="right", padx=5)

        # Tabbed Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        # Tab 1: Resumen / Métricas
        self.tab_summary = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_summary, text="📊 Resumen y Métricas")
        self._setup_summary_tab()

        # Tab 2: Paquetes Requeridos
        self.tab_packages = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_packages, text="📦 Paquetes Requeridos")
        self._setup_packages_tab()

        # Tab 3: Assets Detallados
        self.tab_assets = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_assets, text="🎨 Mallas y Texturas")
        self._setup_assets_tab()

        # Tab 4: Terreno & Actores
        self.tab_terrain = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_terrain, text="🏔️ Terreno & Actores")
        self._setup_terrain_tab()

        # Tab 5: Extractor UTX Nativo
        self.tab_utx = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_utx, text="🖼️ Extractor UTX")
        self._setup_utx_tab()

        # Tab 6: Optimizador de Texturas
        self.tab_textures = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_textures, text="⚡ Redimensionar Texturas")
        self._setup_textures_tab()

        # Tab 7: Validador de Crónica
        self.tab_validator = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_validator, text="🛡️ Validador de Crónica")
        self._setup_validator_tab()

        # Tab 8: Consola / Logs
        self.tab_logs = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_logs, text="📜 Logs")
        self._setup_logs_tab()

        # Status Bar
        self.status_var = tk.StringVar(value="Listo.")
        status_bar = ttk.Frame(self.root, padding=4)
        status_bar.pack(fill="x", side="bottom")
        ttk.Label(status_bar, textvariable=self.status_var, font=("Segoe UI", 8), foreground=self.text_muted).pack(side="left", padx=8)

    def _setup_summary_tab(self):
        self.cards_frame = ttk.Frame(self.tab_summary)
        self.cards_frame.pack(fill="x", pady=6)

        self.metric_vars = {
            "size": tk.StringVar(value="-"),
            "ver": tk.StringVar(value="-"),
            "meshes": tk.StringVar(value="-"),
            "textures": tk.StringVar(value="-"),
            "sounds": tk.StringVar(value="-"),
            "missing": tk.StringVar(value="-"),
        }

        cards = [
            ("Tamaño Mapa", "size"),
            ("Versión Engine", "ver"),
            ("Paquetes Mallas", "meshes"),
            ("Paquetes Texturas", "textures"),
            ("Paquetes Sonidos", "sounds"),
            ("Faltantes en Cliente", "missing"),
        ]

        for i, (label, key) in enumerate(cards):
            card = ttk.Frame(self.cards_frame, style="Card.TFrame", padding=12)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            self.cards_frame.columnconfigure(i, weight=1)

            ttk.Label(card, text=label, style="MetricLbl.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=self.metric_vars[key], style="MetricVal.TLabel").pack(anchor="w", pady=(4, 0))

        ttk.Label(self.tab_summary, text="Detalle de Análisis:", font=("Segoe UI", 10, "bold"), foreground=self.accent_color).pack(anchor="w", pady=(16, 4))
        self.txt_summary = tk.Text(self.tab_summary, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat", wrap="word")
        self.txt_summary.pack(fill="both", expand=True)

    def _setup_packages_tab(self):
        cols = ("cat", "pkg", "ext", "status", "size", "ref_mode", "refs")
        self.tree_pkgs = ttk.Treeview(self.tab_packages, columns=cols, show="headings", selectmode="browse")

        self.tree_pkgs.heading("cat", text="Categoría")
        self.tree_pkgs.heading("pkg", text="Paquete")
        self.tree_pkgs.heading("ext", text="Ext")
        self.tree_pkgs.heading("status", text="Estado")
        self.tree_pkgs.heading("size", text="Tamaño")
        self.tree_pkgs.heading("ref_mode", text="Tipo Ref.")
        self.tree_pkgs.heading("refs", text="Referenciado Por")

        self.tree_pkgs.column("cat", width=120)
        self.tree_pkgs.column("pkg", width=180)
        self.tree_pkgs.column("ext", width=60)
        self.tree_pkgs.column("status", width=90)
        self.tree_pkgs.column("size", width=90)
        self.tree_pkgs.column("ref_mode", width=120)
        self.tree_pkgs.column("refs", width=280)

        scroll = ttk.Scrollbar(self.tab_packages, orient="vertical", command=self.tree_pkgs.yview)
        self.tree_pkgs.configure(yscrollcommand=scroll.set)

        self.tree_pkgs.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _setup_assets_tab(self):
        paned = tk.PanedWindow(self.tab_assets, orient="horizontal", bg=self.bg_color, sashrelief="flat", bd=0)
        paned.pack(fill="both", expand=True)

        frame_left = ttk.Frame(paned, padding=4)
        ttk.Label(frame_left, text="Static Meshes Utilizados:", font=("Segoe UI", 10, "bold"), foreground=self.accent_color).pack(anchor="w", pady=4)
        self.list_meshes = tk.Listbox(frame_left, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.list_meshes.pack(fill="both", expand=True)
        paned.add(frame_left, weight=1)

        frame_right = ttk.Frame(paned, padding=4)
        ttk.Label(frame_right, text="Texturas y Shaders:", font=("Segoe UI", 10, "bold"), foreground=self.accent_color).pack(anchor="w", pady=4)
        self.list_textures = tk.Listbox(frame_right, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.list_textures.pack(fill="both", expand=True)
        paned.add(frame_right, weight=1)

    def _setup_terrain_tab(self):
        top_frame = ttk.Frame(self.tab_terrain, style="Card.TFrame", padding=12)
        top_frame.pack(fill="x", pady=(0, 8))

        self.lbl_terrain_map = ttk.Label(top_frame, text="Heightmap: Ninguno analizado", style="Card.TLabel", font=("Segoe UI", 10, "bold"))
        self.lbl_terrain_map.pack(anchor="w")

        self.lbl_terrain_scale = ttk.Label(top_frame, text="Escala de Terreno: -", style="Card.TLabel", foreground=self.text_muted)
        self.lbl_terrain_scale.pack(anchor="w", pady=(2, 0))

        paned = tk.PanedWindow(self.tab_terrain, orient="horizontal", bg=self.bg_color, sashrelief="flat", bd=0)
        paned.pack(fill="both", expand=True)

        # Left: Placed Mesh Census
        f_left = ttk.Frame(paned, padding=4)
        ttk.Label(f_left, text="Instancias de Modelos 3D en el Mapa:", font=("Segoe UI", 10, "bold"), foreground=self.accent_color).pack(anchor="w", pady=4)
        self.tree_instances = ttk.Treeview(f_left, columns=("mesh", "count"), show="headings", selectmode="browse")
        self.tree_instances.heading("mesh", text="Modelo 3D")
        self.tree_instances.heading("count", text="Cantidad de Colocaciones")
        self.tree_instances.column("mesh", width=320)
        self.tree_instances.column("count", width=140)
        self.tree_instances.pack(fill="both", expand=True)
        paned.add(f_left, weight=1)

        # Right: Actor Classes Census
        f_right = ttk.Frame(paned, padding=4)
        ttk.Label(f_right, text="Clases de Actores Colocados:", font=("Segoe UI", 10, "bold"), foreground=self.accent_color).pack(anchor="w", pady=4)
        self.tree_actors = ttk.Treeview(f_right, columns=("cls", "count"), show="headings", selectmode="browse")
        self.tree_actors.heading("cls", text="Clase Actor")
        self.tree_actors.heading("count", text="Total Actores")
        self.tree_actors.column("cls", width=220)
        self.tree_actors.column("count", width=120)
        self.tree_actors.pack(fill="both", expand=True)
        paned.add(f_right, weight=1)

    def _setup_utx_tab(self):
        ctrl = ttk.Frame(self.tab_utx, style="Card.TFrame", padding=12)
        ctrl.pack(fill="x", pady=(0, 8))

        f_pkg = ttk.Frame(ctrl, style="Card.TFrame")
        f_pkg.pack(fill="x", pady=2)
        ttk.Label(f_pkg, text="Paquete UTX:", style="Card.TLabel", width=14).pack(side="left")
        self.entry_utx_target = tk.Entry(f_pkg, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_utx_target.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(f_pkg, text="Examinar...", command=self._browse_utx_file).pack(side="right")

        f_actions = ttk.Frame(ctrl, style="Card.TFrame")
        f_actions.pack(fill="x", pady=(8, 0))

        ttk.Button(f_actions, text="🔍 Listar Texturas", style="Primary.TButton", command=self._on_list_utx).pack(side="left", padx=4)
        ttk.Button(f_actions, text="💾 Extraer Todas a DDS/PNG", style="Action.TButton", command=self._on_extract_utx).pack(side="left", padx=8)

        # UTX Texture Tree
        cols = ("name", "cls", "dim", "fmt", "mips", "size")
        self.tree_utx = ttk.Treeview(self.tab_utx, columns=cols, show="headings", selectmode="browse")
        self.tree_utx.heading("name", text="Textura")
        self.tree_utx.heading("cls", text="Clase")
        self.tree_utx.heading("dim", text="Dimensiones")
        self.tree_utx.heading("fmt", text="Formato")
        self.tree_utx.heading("mips", text="Mipmaps")
        self.tree_utx.heading("size", text="Tamaño Serial")

        self.tree_utx.column("name", width=200)
        self.tree_utx.column("cls", width=100)
        self.tree_utx.column("dim", width=100)
        self.tree_utx.column("fmt", width=150)
        self.tree_utx.column("mips", width=80)
        self.tree_utx.column("size", width=100)

        scroll = ttk.Scrollbar(self.tab_utx, orient="vertical", command=self.tree_utx.yview)
        self.tree_utx.configure(yscrollcommand=scroll.set)

        self.tree_utx.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _setup_textures_tab(self):
        panel = ttk.Frame(self.tab_textures, style="Card.TFrame", padding=16)
        panel.pack(fill="x", pady=6)

        ttk.Label(panel, text="Herramienta de Reducción de Texturas por Lote", font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(panel, text="Redimensiona texturas (.png, .tga, .dds, .bmp) forzando potencias de dos para no crashear el motor viejo.", style="Card.TLabel", foreground=self.text_muted).pack(anchor="w", pady=(0, 12))

        f1 = ttk.Frame(panel, style="Card.TFrame")
        f1.pack(fill="x", pady=4)
        ttk.Label(f1, text="Carpeta con Texturas:", style="Card.TLabel", width=20).pack(side="left")
        self.entry_tex_folder = tk.Entry(f1, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_tex_folder.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(f1, text="Examinar...", command=self._browse_tex_folder).pack(side="right")

        f2 = ttk.Frame(panel, style="Card.TFrame")
        f2.pack(fill="x", pady=4)
        ttk.Label(f2, text="Carpeta de Salida:", style="Card.TLabel", width=20).pack(side="left")
        self.entry_tex_out = tk.Entry(f2, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_tex_out.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(f2, text="Examinar...", command=self._browse_tex_out).pack(side="right")

        f3 = ttk.Frame(panel, style="Card.TFrame")
        f3.pack(fill="x", pady=8)
        ttk.Label(f3, text="Resolución Máxima:", style="Card.TLabel", width=20).pack(side="left")
        self.combo_res = ttk.Combobox(f3, values=["512", "1024", "256", "2048"], state="readonly", width=10)
        self.combo_res.set("512")
        self.combo_res.pack(side="left", padx=6)

        self.btn_resize = ttk.Button(f3, text="⚡ Iniciar Reducción", style="Action.TButton", command=self._on_start_resize)
        self.btn_resize.pack(side="left", padx=16)

        self.prog_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.tab_textures, variable=self.prog_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=12)

        self.txt_resize_log = tk.Text(self.tab_textures, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat", height=10)
        self.txt_resize_log.pack(fill="both", expand=True)

    def _setup_validator_tab(self):
        panel = ttk.Frame(self.tab_validator, style="Card.TFrame", padding=16)
        panel.pack(fill="x", pady=6)

        ttk.Label(panel, text="Validador de Compatibilidad con Crónicas Bajas", font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(panel, text="Detecta si el mapa contiene actores, clases de shaders o versiones que crashean motores viejos (C4 / Interlude).", style="Card.TLabel", foreground=self.text_muted).pack(anchor="w", pady=(0, 12))

        f_sel = ttk.Frame(panel, style="Card.TFrame")
        f_sel.pack(fill="x", pady=4)
        ttk.Label(f_sel, text="Crónica Objetivo:", style="Card.TLabel", width=18).pack(side="left")
        self.combo_target_chronicle = ttk.Combobox(f_sel, values=["C4 (Scions of Destiny)", "Interlude (The Chaotic Throne)", "High Five"], state="readonly", width=30)
        self.combo_target_chronicle.set("C4 (Scions of Destiny)")
        self.combo_target_chronicle.pack(side="left", padx=6)

        ttk.Button(f_sel, text="🛡️ Validar Compatibilidad", style="Primary.TButton", command=self._on_validate_chronicle).pack(side="left", padx=12)

        cols = ("sev", "cat", "item", "msg", "fix")
        self.tree_val = ttk.Treeview(self.tab_validator, columns=cols, show="headings", selectmode="browse")
        self.tree_val.heading("sev", text="Gravedad")
        self.tree_val.heading("cat", text="Categoría")
        self.tree_val.heading("item", text="Elemento")
        self.tree_val.heading("msg", text="Diagnóstico")
        self.tree_val.heading("fix", text="Solución Recomendada")

        self.tree_val.column("sev", width=90)
        self.tree_val.column("cat", width=130)
        self.tree_val.column("item", width=160)
        self.tree_val.column("msg", width=320)
        self.tree_val.column("fix", width=300)

        scroll = ttk.Scrollbar(self.tab_validator, orient="vertical", command=self.tree_val.yview)
        self.tree_val.configure(yscrollcommand=scroll.set)

        self.tree_val.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _setup_logs_tab(self):
        self.txt_logs = tk.Text(self.tab_logs, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.txt_logs.pack(fill="both", expand=True)

    # --- Callbacks ---
    def _log(self, msg: str):
        self.txt_logs.insert("end", msg + "\n")
        self.txt_logs.see("end")

    def _browse_unr(self):
        path = filedialog.askopenfilename(title="Seleccionar mapa .unr", filetypes=[("Unreal Maps", "*.unr"), ("Todos los archivos", "*.*")])
        if path:
            self.entry_unr.delete(0, "end")
            self.entry_unr.insert(0, path)
            p = Path(path)
            if not self.entry_output.get():
                self.entry_output.insert(0, str(p.parent / f"Export_{p.stem}"))

    def _browse_client(self):
        folder = filedialog.askdirectory(title="Seleccionar cliente de Lineage 2")
        if folder:
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, folder)

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta destino")
        if folder:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, folder)

    def _browse_tex_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de texturas")
        if folder:
            self.entry_tex_folder.delete(0, "end")
            self.entry_tex_folder.insert(0, folder)

    def _browse_tex_out(self):
        folder = filedialog.askdirectory(title="Carpeta destino de texturas reducidas")
        if folder:
            self.entry_tex_out.delete(0, "end")
            self.entry_tex_out.insert(0, folder)

    def _browse_utx_file(self):
        path = filedialog.askopenfilename(title="Seleccionar paquete UTX", filetypes=[("Unreal Textures", "*.utx"), ("Todos los archivos", "*.*")])
        if path:
            self.entry_utx_target.delete(0, "end")
            self.entry_utx_target.insert(0, path)

    def _on_analyze(self):
        unr_path = self.entry_unr.get().strip()
        if not unr_path or not os.path.exists(unr_path):
            messagebox.showerror("Error", "Seleccione un archivo de mapa .unr válido.")
            return

        client_path = self.entry_client.get().strip()
        deep_scan = self.var_deep_scan.get()

        self.status_var.set("Analizando mapa...")
        self.btn_analyze.config(state="disabled")

        def worker():
            try:
                self._log(f"--- Analizando: {Path(unr_path).name} ---")
                analyzer = UNRAnalyzer(client_root=client_path if client_path else None)
                res = analyzer.analyze_map(unr_path, deep_mesh_scan=deep_scan)
                self.analysis_result = res

                # Inspect Terrain & Placed Meshes
                inspector = MapInspector.load_from_file(unr_path)
                census = inspector.inspect()

                # Generate reports
                out_dir = self.entry_output.get().strip()
                if out_dir:
                    p_out = Path(out_dir)
                    p_out.mkdir(parents=True, exist_ok=True)
                    gen = ManifestGenerator(res)
                    gen.save_json(p_out / f"{res.map_path.stem}_manifest.json")
                    html_path = gen.save_html(p_out / f"{res.map_path.stem}_report.html")
                    gen.save_markdown(p_out / f"{res.map_path.stem}_report.md")
                    self.last_html_report = html_path

                self.root.after(0, lambda: self._update_ui_with_results(census))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error al analizar", str(e)))
                self.root.after(0, lambda: self._log(f"[ERROR] {e}"))
            finally:
                self.root.after(0, lambda: self.btn_analyze.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set("Análisis completado."))

        threading.Thread(target=worker, daemon=True).start()

    def _update_ui_with_results(self, census: MapCensus):
        res = self.analysis_result
        if not res:
            return

        # 1. Update Metrics
        self.metric_vars["size"].set(format_bytes(res.map_size))
        ver_text = f"v{res.unreal_version}"
        if res.l2_crypt_version:
            ver_text += f" (L2:{res.l2_crypt_version})"
        self.metric_vars["ver"].set(ver_text)
        self.metric_vars["meshes"].set(str(len(res.static_mesh_packages)))
        self.metric_vars["textures"].set(str(len(res.texture_packages)))
        self.metric_vars["sounds"].set(str(len(res.sound_packages)))
        self.metric_vars["missing"].set(str(len(res.missing_packages)))

        # 2. Text Summary
        self.txt_summary.delete("1.0", "end")
        summary_text = (
            f"Mapa: {res.map_name}\n"
            f"Ruta: {res.map_path}\n"
            f"Versión Engine: UE2 {res.unreal_version} | Licensee: {res.licensee_mode}\n"
            f"Total Names: {res.total_names} | Total Imports: {res.total_imports} | Total Exports: {res.total_exports}\n\n"
            f"Paquetes de Mallas (.usx): {len(res.static_mesh_packages)}\n"
            f"Paquetes de Texturas (.utx): {len(res.texture_packages)}\n"
            f"Paquetes de Sonidos (.uax): {len(res.sound_packages)}\n"
            f"Modelos 3D referenciados: {len(res.static_meshes_used)}\n"
            f"Texturas y Shaders referenciados: {len(res.textures_used) + len(res.shaders_used)}\n"
        )
        if res.missing_packages:
            summary_text += f"\n[ALERTA] {len(res.missing_packages)} paquetes no se encontraron en el cliente:\n"
            for m in res.missing_packages:
                summary_text += f" - {m}\n"
        self.txt_summary.insert("end", summary_text)

        # 3. Packages TreeView
        for item in self.tree_pkgs.get_children():
            self.tree_pkgs.delete(item)

        all_pkgs = list(res.all_packages().values())
        all_pkgs.sort(key=lambda p: (p.category, p.name.lower()))
        for pkg in all_pkgs:
            status_str = "ENCONTRADO" if pkg.found else "FALTANTE"
            ref_mode = "Directo" if pkg.direct else "Cascada (Malla)"
            refs = ", ".join(pkg.referenced_by) if pkg.referenced_by else "-"
            size_str = format_bytes(pkg.file_size) if pkg.found else "-"

            self.tree_pkgs.insert("", "end", values=(
                pkg.category, pkg.name, pkg.expected_extension, status_str, size_str, ref_mode, refs
            ))

        # 4. Assets List
        self.list_meshes.delete(0, "end")
        for m in res.static_meshes_used:
            self.list_meshes.insert("end", m)

        self.list_textures.delete(0, "end")
        for t in res.textures_used:
            self.list_textures.insert("end", f"[Texture] {t}")
        for s in res.shaders_used:
            self.list_textures.insert("end", f"[Shader]  {s}")

        # 5. Terrain & Actors Census Tab
        if census.terrain:
            self.lbl_terrain_map.config(text=f"Heightmap: {census.terrain.heightmap_texture}")
            self.lbl_terrain_scale.config(text=f"Escala de Terreno: X={census.terrain.terrain_scale[0]}, Y={census.terrain.terrain_scale[1]}, Z={census.terrain.terrain_scale[2]}")

        for item in self.tree_instances.get_children():
            self.tree_instances.delete(item)
        for mesh, cnt in census.static_mesh_usage.items():
            self.tree_instances.insert("", "end", values=(mesh, f"{cnt} veces"))

        for item in self.tree_actors.get_children():
            self.tree_actors.delete(item)
        for cls_name, cnt in census.actor_class_counts.items():
            self.tree_actors.insert("", "end", values=(cls_name, cnt))

        self._log(f"Análisis completado para {res.map_name}: {len(res.all_packages())} paquetes identificados.")

    def _on_export(self):
        if not self.analysis_result:
            messagebox.showwarning("Atención", "Primero debe analizar un mapa.")
            return

        out_dir = self.entry_output.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Especifique una carpeta de salida.")
            return

        self.status_var.set("Copiando paquetes...")
        self.btn_export.config(state="disabled")

        def worker():
            try:
                collector = AssetCollector(target_directory=out_dir)
                summary = collector.export_dependencies(self.analysis_result)
                msg = f"Se copiaron {len(summary.copied_files)} archivos ({format_bytes(summary.total_bytes_copied)})."
                if summary.missing_files:
                    msg += f"\n{len(summary.missing_files)} paquetes no se encontraron en el cliente."
                self.root.after(0, lambda: messagebox.showinfo("Exportación Finalizada", msg))
                self.root.after(0, lambda: self._log(f"[EXPORT] {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error al exportar", str(e)))
            finally:
                self.root.after(0, lambda: self.btn_export.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set("Exportación finalizada."))

        threading.Thread(target=worker, daemon=True).start()

    def _on_list_utx(self):
        utx_path = self.entry_utx_target.get().strip()
        if not utx_path or not os.path.exists(utx_path):
            messagebox.showerror("Error", "Seleccione un archivo .utx válido.")
            return

        for item in self.tree_utx.get_children():
            self.tree_utx.delete(item)

        try:
            self.active_utx_extractor = UTXExtractor(utx_path)
            textures = self.active_utx_extractor.list_textures()
            for name, cls, size, _ in textures:
                item = self.active_utx_extractor.extract_texture(name)
                dim_str = f"{item.width}x{item.height}" if item else "-"
                fmt_str = item.format_name if item else "-"
                mips_str = str(item.mip_count) if item else "-"

                self.tree_utx.insert("", "end", values=(
                    name, cls, dim_str, fmt_str, mips_str, format_bytes(size)
                ))
            self._log(f"UTX {Path(utx_path).name}: {len(textures)} texturas encontradas.")
        except Exception as e:
            messagebox.showerror("Error al leer UTX", str(e))

    def _on_extract_utx(self):
        if not self.active_utx_extractor:
            self._on_list_utx()
        if not self.active_utx_extractor:
            return

        out_dir = filedialog.askdirectory(title="Seleccionar carpeta donde guardar las imágenes extraídas")
        if not out_dir:
            return

        self.status_var.set("Extrayendo texturas...")

        def worker():
            try:
                paths = self.active_utx_extractor.export_all_to_folder(out_dir, export_png=True, export_dds=True)
                msg = f"Se extrajeron {len(paths)} archivos (.dds y .png) en {out_dir}"
                self.root.after(0, lambda: messagebox.showinfo("Extracción Completa", msg))
                self.root.after(0, lambda: self._log(f"[UTX EXTRACTION] {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error al extraer", str(e)))
            finally:
                self.root.after(0, lambda: self.status_var.set("Listo."))

        threading.Thread(target=worker, daemon=True).start()

    def _on_start_resize(self):
        src_dir = self.entry_tex_folder.get().strip()
        if not src_dir or not os.path.exists(src_dir):
            messagebox.showerror("Error", "Seleccione una carpeta válida con texturas.")
            return

        max_dim = int(self.combo_res.get())
        dst_dir = self.entry_tex_out.get().strip()
        if not dst_dir:
            dst_dir = str(Path(src_dir).parent / f"{Path(src_dir).name}_{max_dim}")
            self.entry_tex_out.delete(0, "end")
            self.entry_tex_out.insert(0, dst_dir)

        self.btn_resize.config(state="disabled")
        self.txt_resize_log.delete("1.0", "end")
        self.prog_var.set(0)

        def worker():
            try:
                def progress(current, total, name):
                    pct = (current / total) * 100
                    self.prog_var.set(pct)
                    self.status_var.set(f"Procesando ({current}/{total}): {name}")

                records = batch_resize_folder(
                    src_folder=src_dir,
                    dst_folder=dst_dir,
                    max_dimension=max_dim,
                    progress_callback=progress,
                )
                success = sum(1 for r in records if r.success)
                saved_bytes = sum(max(0, r.original_bytes - r.new_bytes) for r in records if r.success)

                report = (
                    f"--- Reducción Finalizada ---\n"
                    f"Procesadas: {success} / {len(records)} imágenes\n"
                    f"Espacio ahorrado: {format_bytes(saved_bytes)}\n"
                    f"Carpeta de salida: {dst_dir}\n"
                )
                self.root.after(0, lambda: self.txt_resize_log.insert("end", report))
                self.root.after(0, lambda: messagebox.showinfo("Optimización Completa", report))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.root.after(0, lambda: self.btn_resize.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set("Listo."))

        threading.Thread(target=worker, daemon=True).start()

    def _on_validate_chronicle(self):
        unr_path = self.entry_unr.get().strip()
        if not unr_path or not os.path.exists(unr_path):
            messagebox.showerror("Error", "Seleccione un archivo de mapa .unr primero.")
            return

        choice = self.combo_target_chronicle.get()
        target_code = "c4"
        if "interlude" in choice.lower():
            target_code = "interlude"
        elif "high five" in choice.lower():
            target_code = "h5"

        for item in self.tree_val.get_children():
            self.tree_val.delete(item)

        try:
            val = ChronicleValidator(target_chronicle=target_code)
            rep = val.validate_map(unr_path)

            for issue in rep.issues:
                self.tree_val.insert("", "end", values=(
                    issue.severity, issue.category, issue.item_name, issue.message, issue.recommendation
                ))

            if rep.is_compatible:
                messagebox.showinfo("Validación Exitosa", f"El mapa es compatible con {choice} sin errores críticos.")
            else:
                messagebox.showwarning(
                    "Problemas Detectados",
                    f"Se encontraron {rep.critical_count()} errores críticos que crashearán {choice}.\nRevise la tabla para ver las soluciones."
                )
        except Exception as e:
            messagebox.showerror("Error de Validación", str(e))

    def _open_html_report(self):
        if self.last_html_report and self.last_html_report.exists():
            webbrowser.open(str(self.last_html_report))
        else:
            out_dir = self.entry_output.get().strip()
            if out_dir and os.path.exists(out_dir):
                htmls = list(Path(out_dir).glob("*_report.html"))
                if htmls:
                    webbrowser.open(str(htmls[0]))
                    return
            messagebox.showinfo("Reporte", "Aún no se ha generado un reporte HTML. Analice un mapa primero.")

    def _open_output_folder(self):
        out_dir = self.entry_output.get().strip()
        if out_dir and os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            messagebox.showinfo("Carpeta", "La carpeta de salida aún no existe.")


def main():
    root = tk.Tk()
    app = UNRToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
