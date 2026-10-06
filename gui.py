#!/usr/bin/env python3
"""
Graphical User Interface (GUI) for UNR Tool v1.7
Modern Tkinter desktop application for analyzing, isolating, extracting, downporting,
and transmigrating Lineage 2 maps. Supports full English and Russian localization.
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
from map_comparator import MapComparator, MapDiffResult
from map_isolator import MapIsolator, MapIsolationResult
from i18n import i18n


def get_default_client_dir() -> str:
    env_dir = os.environ.get("L2_CLIENT_DIR", "")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "2-Juego",
        Path("./Client"),
        Path("C:/Lineage2/Client"),
    ]
    for c in candidates:
        if c.is_dir():
            return str(c)
    return ""


DEFAULT_CLIENT_DIR = get_default_client_dir()


class UNRToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(i18n("app_title"))
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)

        # State
        self.analysis_result: MapAnalysisResult | None = None
        self.last_html_report: Path | None = None
        self.active_utx_extractor: UTXExtractor | None = None
        self.last_diff_result: MapDiffResult | None = None

        # Localization registry: lists of (widget, key, attribute)
        self._i18n_elements = []
        self._i18n_tabs = []
        self._i18n_headings = []

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
        style.configure("Lang.TButton", background="#4b5563", foreground="#ffffff", font=("Segoe UI", 9, "bold"), padding=[8, 4])
        style.map("Lang.TButton", background=[("active", "#374151")])

    # --- Localization Helpers ---
    def _reg_text(self, widget, key: str, attr: str = "text"):
        self._i18n_elements.append((widget, key, attr))
        try:
            widget[attr] = i18n(key)
        except Exception:
            pass
        return widget

    def _reg_tab(self, tab_frame, key: str):
        self._i18n_tabs.append((tab_frame, key))
        self.notebook.add(tab_frame, text=i18n(key))

    def _reg_heading(self, tree, col: str, key: str):
        self._i18n_headings.append((tree, col, key))
        tree.heading(col, text=i18n(key))

    def _toggle_language(self):
        new_lang = "ru" if i18n.current_lang == "en" else "en"
        i18n.set_language(new_lang)
        self._update_language_ui()

    def _update_language_ui(self):
        self.root.title(i18n("app_title"))
        self.btn_lang.config(text=i18n("lang_switch_btn"))
        for widget, key, attr in self._i18n_elements:
            try:
                widget[attr] = i18n(key)
            except Exception:
                pass
        for tab_frame, key in self._i18n_tabs:
            try:
                self.notebook.tab(tab_frame, text=i18n(key))
            except Exception:
                pass
        for tree, col, key in self._i18n_headings:
            try:
                tree.heading(col, text=i18n(key))
            except Exception:
                pass

    def _create_layout(self):
        # Header banner
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")
        
        lbl_head = ttk.Label(header, text=i18n("header_title"), style="Header.TLabel")
        lbl_head.pack(side="left")
        self._reg_text(lbl_head, "header_title")

        lbl_sub = ttk.Label(header, text=i18n("header_subtitle"), foreground=self.text_muted)
        lbl_sub.pack(side="left", padx=10, pady=(4, 0))
        self._reg_text(lbl_sub, "header_subtitle")

        # Language Switcher Button (Top Right)
        self.btn_lang = ttk.Button(header, text=i18n("lang_switch_btn"), style="Lang.TButton", command=self._toggle_language)
        self.btn_lang.pack(side="right", padx=6)

        # Main Input Control Panel
        control_panel = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        control_panel.pack(fill="x", padx=12, pady=6)

        # UNR File selector
        r1 = ttk.Frame(control_panel, style="Card.TFrame")
        r1.pack(fill="x", pady=2)
        lbl_unr = ttk.Label(r1, text=i18n("label_map"), style="Card.TLabel", width=18)
        lbl_unr.pack(side="left")
        self._reg_text(lbl_unr, "label_map")
        self.entry_unr = tk.Entry(r1, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_unr.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_unr = ttk.Button(r1, text=i18n("btn_browse"), command=self._browse_unr)
        btn_br_unr.pack(side="right")
        self._reg_text(btn_br_unr, "btn_browse")

        # Client Root selector
        r2 = ttk.Frame(control_panel, style="Card.TFrame")
        r2.pack(fill="x", pady=2)
        lbl_client = ttk.Label(r2, text=i18n("label_client"), style="Card.TLabel", width=18)
        lbl_client.pack(side="left")
        self._reg_text(lbl_client, "label_client")
        self.entry_client = tk.Entry(r2, bg="#111827", fg=self.text_color, insertbackground="white")
        if os.path.exists(DEFAULT_CLIENT_DIR):
            self.entry_client.insert(0, DEFAULT_CLIENT_DIR)
        self.entry_client.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_cli = ttk.Button(r2, text=i18n("btn_browse"), command=self._browse_client)
        btn_br_cli.pack(side="right")
        self._reg_text(btn_br_cli, "btn_browse")

        # Output Folder selector
        r3 = ttk.Frame(control_panel, style="Card.TFrame")
        r3.pack(fill="x", pady=2)
        lbl_out = ttk.Label(r3, text=i18n("label_output"), style="Card.TLabel", width=18)
        lbl_out.pack(side="left")
        self._reg_text(lbl_out, "label_output")
        self.entry_output = tk.Entry(r3, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_output.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_out = ttk.Button(r3, text=i18n("btn_browse"), command=self._browse_output)
        btn_br_out.pack(side="right")
        self._reg_text(btn_br_out, "btn_browse")

        # Options & Action Buttons Bar
        action_bar = ttk.Frame(control_panel, style="Card.TFrame")
        action_bar.pack(fill="x", pady=(8, 0))

        self.var_deep_scan = tk.BooleanVar(value=True)
        self.cb_deep = tk.Checkbutton(
            action_bar, text=i18n("chk_deep_scan"),
            variable=self.var_deep_scan, bg=self.panel_bg, fg=self.text_color,
            selectcolor=self.bg_color, activebackground=self.panel_bg, activeforeground=self.text_color
        )
        self.cb_deep.pack(side="left", padx=5)
        self._reg_text(self.cb_deep, "chk_deep_scan")

        self.btn_analyze = ttk.Button(action_bar, text=i18n("btn_analyze"), style="Primary.TButton", command=self._on_analyze)
        self.btn_analyze.pack(side="left", padx=8)
        self._reg_text(self.btn_analyze, "btn_analyze")

        self.btn_export = ttk.Button(action_bar, text=i18n("btn_export"), style="Action.TButton", command=self._on_export)
        self.btn_export.pack(side="left", padx=5)
        self._reg_text(self.btn_export, "btn_export")

        self.btn_open_html = ttk.Button(action_bar, text=i18n("btn_open_html"), command=self._open_html_report)
        self.btn_open_html.pack(side="right", padx=5)
        self._reg_text(self.btn_open_html, "btn_open_html")

        self.btn_open_folder = ttk.Button(action_bar, text=i18n("btn_open_folder"), command=self._open_output_folder)
        self.btn_open_folder.pack(side="right", padx=5)
        self._reg_text(self.btn_open_folder, "btn_open_folder")

        # Tabbed Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=8)

        # Tab 1: Summary / Metrics
        self.tab_summary = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_summary, "tab_summary")
        self._setup_summary_tab()

        # Tab 2: Required Packages
        self.tab_packages = ttk.Frame(self.notebook, padding=8)
        self._reg_tab(self.tab_packages, "tab_packages")
        self._setup_packages_tab()

        # Tab 3: Detailed Assets
        self.tab_assets = ttk.Frame(self.notebook, padding=8)
        self._reg_tab(self.tab_assets, "tab_assets")
        self._setup_assets_tab()

        # Tab 4: Terrain & Actors
        self.tab_terrain = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_terrain, "tab_terrain")
        self._setup_terrain_tab()

        # Tab 5: Native UTX Extractor
        self.tab_utx = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_utx, "tab_utx")
        self._setup_utx_tab()

        # Tab 6: Texture Optimizer
        self.tab_textures = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_textures, "tab_textures")
        self._setup_textures_tab()

        # Tab 7: Chronicle Validator
        self.tab_validator = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_validator, "tab_validator")
        self._setup_validator_tab()

        # Tab 8: Map Diff / Comparator
        self.tab_diff = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_diff, "tab_diff")
        self._setup_diff_tab()

        # Tab 9: Autonomous Single-Package Isolator (1/Class)
        self.tab_isolate = ttk.Frame(self.notebook, padding=12)
        self._reg_tab(self.tab_isolate, "tab_isolate")
        self._setup_isolate_tab()

        # Tab 10: Execution Logs
        self.tab_logs = ttk.Frame(self.notebook, padding=8)
        self._reg_tab(self.tab_logs, "tab_logs")
        self._setup_logs_tab()

        # Status Bar
        self.status_var = tk.StringVar(value=i18n("status_ready"))
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
            ("card_unr_size", "size"),
            ("card_sector", "ver"),
            ("card_packages", "meshes"),
            ("card_total_assets", "textures"),
            ("card_total_size", "sounds"),
            ("card_packages", "missing"),
        ]

        for i, (key, var_key) in enumerate(cards):
            card = ttk.Frame(self.cards_frame, style="Card.TFrame", padding=12)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            self.cards_frame.columnconfigure(i, weight=1)

            lbl = ttk.Label(card, text=i18n(key), style="MetricLbl.TLabel")
            lbl.pack(anchor="w")
            self._reg_text(lbl, key)
            ttk.Label(card, textvariable=self.metric_vars[var_key], style="MetricVal.TLabel").pack(anchor="w", pady=(4, 0))

        lbl_sec = ttk.Label(self.tab_summary, text=i18n("sec_distribution"), font=("Segoe UI", 10, "bold"), foreground=self.accent_color)
        lbl_sec.pack(anchor="w", pady=(16, 4))
        self._reg_text(lbl_sec, "sec_distribution")

        self.txt_summary = tk.Text(self.tab_summary, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat", wrap="word")
        self.txt_summary.pack(fill="both", expand=True)

    def _setup_packages_tab(self):
        cols = ("cat", "pkg", "ext", "status", "size", "ref_mode", "refs")
        self.tree_pkgs = ttk.Treeview(self.tab_packages, columns=cols, show="headings", selectmode="browse")

        self._reg_heading(self.tree_pkgs, "cat", "col_pkg_type")
        self._reg_heading(self.tree_pkgs, "pkg", "col_pkg_name")
        self._reg_heading(self.tree_pkgs, "ext", "col_pkg_ext")
        self._reg_heading(self.tree_pkgs, "status", "col_pkg_status")
        self._reg_heading(self.tree_pkgs, "size", "col_pkg_size")
        self._reg_heading(self.tree_pkgs, "ref_mode", "col_pkg_refmode")
        self._reg_heading(self.tree_pkgs, "refs", "col_pkg_refs")

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
        paned = ttk.PanedWindow(self.tab_assets, orient="horizontal")
        paned.pack(fill="both", expand=True)

        frame_left = ttk.Frame(paned, padding=4)
        lbl_m = ttk.Label(frame_left, text=i18n("lbl_used_meshes"), font=("Segoe UI", 10, "bold"), foreground=self.accent_color)
        lbl_m.pack(anchor="w", pady=4)
        self._reg_text(lbl_m, "lbl_used_meshes")
        self.list_meshes = tk.Listbox(frame_left, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.list_meshes.pack(fill="both", expand=True)
        paned.add(frame_left, weight=1)

        frame_right = ttk.Frame(paned, padding=4)
        lbl_t = ttk.Label(frame_right, text=i18n("lbl_used_textures"), font=("Segoe UI", 10, "bold"), foreground=self.accent_color)
        lbl_t.pack(anchor="w", pady=4)
        self._reg_text(lbl_t, "lbl_used_textures")
        self.list_textures = tk.Listbox(frame_right, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.list_textures.pack(fill="both", expand=True)
        paned.add(frame_right, weight=1)

    def _setup_terrain_tab(self):
        top_frame = ttk.Frame(self.tab_terrain, style="Card.TFrame", padding=12)
        top_frame.pack(fill="x", pady=(0, 8))

        lbl_top = ttk.Label(top_frame, text=i18n("terrain_title"), style="Card.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.accent_color)
        lbl_top.pack(anchor="w")
        self._reg_text(lbl_top, "terrain_title")

        lbl_desc = ttk.Label(top_frame, text=i18n("terrain_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_desc.pack(anchor="w", pady=(2, 6))
        self._reg_text(lbl_desc, "terrain_desc")

        self.lbl_terrain_map = ttk.Label(top_frame, text="Heightmap: -", style="Card.TLabel", font=("Segoe UI", 9, "bold"))
        self.lbl_terrain_map.pack(anchor="w")

        self.lbl_terrain_scale = ttk.Label(top_frame, text="Terrain Scale: -", style="Card.TLabel", foreground=self.text_muted)
        self.lbl_terrain_scale.pack(anchor="w", pady=(2, 0))

        paned = ttk.PanedWindow(self.tab_terrain, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Left: Placed Mesh Census
        f_left = ttk.Frame(paned, padding=4)
        self.tree_instances = ttk.Treeview(f_left, columns=("mesh", "count"), show="headings", selectmode="browse")
        self._reg_heading(self.tree_instances, "mesh", "col_mesh_name")
        self._reg_heading(self.tree_instances, "count", "col_mesh_count")
        self.tree_instances.column("mesh", width=320)
        self.tree_instances.column("count", width=140)
        self.tree_instances.pack(fill="both", expand=True)
        paned.add(f_left, weight=1)

        # Right: Actor Classes Census
        f_right = ttk.Frame(paned, padding=4)
        self.tree_actors = ttk.Treeview(f_right, columns=("cls", "count"), show="headings", selectmode="browse")
        self._reg_heading(self.tree_actors, "cls", "col_actor_class")
        self._reg_heading(self.tree_actors, "count", "col_actor_total")
        self.tree_actors.column("cls", width=220)
        self.tree_actors.column("count", width=120)
        self.tree_actors.pack(fill="both", expand=True)
        paned.add(f_right, weight=1)

    def _setup_utx_tab(self):
        ctrl = ttk.Frame(self.tab_utx, style="Card.TFrame", padding=12)
        ctrl.pack(fill="x", pady=(0, 8))

        lbl_u_title = ttk.Label(ctrl, text=i18n("utx_title"), font=("Segoe UI", 11, "bold"), foreground=self.accent_color, style="Card.TLabel")
        lbl_u_title.pack(anchor="w")
        self._reg_text(lbl_u_title, "utx_title")

        lbl_u_desc = ttk.Label(ctrl, text=i18n("utx_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_u_desc.pack(anchor="w", pady=(2, 8))
        self._reg_text(lbl_u_desc, "utx_desc")

        f_pkg = ttk.Frame(ctrl, style="Card.TFrame")
        f_pkg.pack(fill="x", pady=2)
        lbl_u_pkg = ttk.Label(f_pkg, text=i18n("lbl_select_utx"), style="Card.TLabel", width=18)
        lbl_u_pkg.pack(side="left")
        self._reg_text(lbl_u_pkg, "lbl_select_utx")
        self.entry_utx_target = tk.Entry(f_pkg, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_utx_target.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_utx = ttk.Button(f_pkg, text=i18n("btn_browse"), command=self._browse_utx_file)
        btn_br_utx.pack(side="right")
        self._reg_text(btn_br_utx, "btn_browse")

        f_actions = ttk.Frame(ctrl, style="Card.TFrame")
        f_actions.pack(fill="x", pady=(8, 0))

        btn_list = ttk.Button(f_actions, text=i18n("btn_list_utx"), style="Primary.TButton", command=self._on_list_utx)
        btn_list.pack(side="left", padx=4)
        self._reg_text(btn_list, "btn_list_utx")

        btn_ext = ttk.Button(f_actions, text=i18n("btn_extract_all_utx"), style="Action.TButton", command=self._on_extract_utx)
        btn_ext.pack(side="left", padx=8)
        self._reg_text(btn_ext, "btn_extract_all_utx")

        # UTX Texture Tree
        cols = ("name", "cls", "dim", "fmt", "mips", "size")
        self.tree_utx = ttk.Treeview(self.tab_utx, columns=cols, show="headings", selectmode="browse")
        self._reg_heading(self.tree_utx, "name", "col_utx_tex")
        self._reg_heading(self.tree_utx, "cls", "col_utx_cls")
        self._reg_heading(self.tree_utx, "dim", "col_utx_dim")
        self._reg_heading(self.tree_utx, "fmt", "col_utx_fmt")
        self._reg_heading(self.tree_utx, "mips", "col_utx_mips")
        self._reg_heading(self.tree_utx, "size", "col_utx_sz")

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

        lbl_t_title = ttk.Label(panel, text=i18n("tex_title"), font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel")
        lbl_t_title.pack(anchor="w", pady=(0, 4))
        self._reg_text(lbl_t_title, "tex_title")

        lbl_t_desc = ttk.Label(panel, text=i18n("tex_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_t_desc.pack(anchor="w", pady=(0, 12))
        self._reg_text(lbl_t_desc, "tex_desc")

        f1 = ttk.Frame(panel, style="Card.TFrame")
        f1.pack(fill="x", pady=4)
        lbl_tf = ttk.Label(f1, text=i18n("lbl_tex_folder"), style="Card.TLabel", width=20)
        lbl_tf.pack(side="left")
        self._reg_text(lbl_tf, "lbl_tex_folder")
        self.entry_tex_folder = tk.Entry(f1, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_tex_folder.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_tf = ttk.Button(f1, text=i18n("btn_browse"), command=self._browse_tex_folder)
        btn_br_tf.pack(side="right")
        self._reg_text(btn_br_tf, "btn_browse")

        f2 = ttk.Frame(panel, style="Card.TFrame")
        f2.pack(fill="x", pady=4)
        lbl_to = ttk.Label(f2, text=i18n("label_output"), style="Card.TLabel", width=20)
        lbl_to.pack(side="left")
        self._reg_text(lbl_to, "label_output")
        self.entry_tex_out = tk.Entry(f2, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_tex_out.pack(side="left", fill="x", expand=True, padx=6)
        btn_br_to = ttk.Button(f2, text=i18n("btn_browse"), command=self._browse_tex_out)
        btn_br_to.pack(side="right")
        self._reg_text(btn_br_to, "btn_browse")

        f3 = ttk.Frame(panel, style="Card.TFrame")
        f3.pack(fill="x", pady=8)
        lbl_res = ttk.Label(f3, text=i18n("lbl_max_dim"), style="Card.TLabel", width=20)
        lbl_res.pack(side="left")
        self._reg_text(lbl_res, "lbl_max_dim")
        self.combo_res = ttk.Combobox(f3, values=["512", "1024", "256", "2048"], state="readonly", width=10)
        self.combo_res.set("512")
        self.combo_res.pack(side="left", padx=6)

        self.btn_resize = ttk.Button(f3, text=i18n("btn_downscale"), style="Action.TButton", command=self._on_start_resize)
        self.btn_resize.pack(side="left", padx=16)
        self._reg_text(self.btn_resize, "btn_downscale")

        self.prog_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.tab_textures, variable=self.prog_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=12)

        self.txt_resize_log = tk.Text(self.tab_textures, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat", height=10)
        self.txt_resize_log.pack(fill="both", expand=True)

    def _setup_validator_tab(self):
        panel = ttk.Frame(self.tab_validator, style="Card.TFrame", padding=16)
        panel.pack(fill="x", pady=6)

        lbl_v_title = ttk.Label(panel, text=i18n("val_title"), font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel")
        lbl_v_title.pack(anchor="w", pady=(0, 4))
        self._reg_text(lbl_v_title, "val_title")

        lbl_v_desc = ttk.Label(panel, text=i18n("val_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_v_desc.pack(anchor="w", pady=(0, 12))
        self._reg_text(lbl_v_desc, "val_desc")

        f_sel = ttk.Frame(panel, style="Card.TFrame")
        f_sel.pack(fill="x", pady=4)
        lbl_tc = ttk.Label(f_sel, text=i18n("lbl_target_chronicle"), style="Card.TLabel", width=18)
        lbl_tc.pack(side="left")
        self._reg_text(lbl_tc, "lbl_target_chronicle")
        self.combo_target_chronicle = ttk.Combobox(f_sel, values=["C4 (Scions of Destiny)", "Interlude (C6)", "High Five (H5)", "Classic"], state="readonly", width=28)
        self.combo_target_chronicle.set("Interlude (C6)")
        self.combo_target_chronicle.pack(side="left", padx=6)

        btn_val = ttk.Button(f_sel, text=i18n("btn_validate"), style="Primary.TButton", command=self._on_validate_chronicle)
        btn_val.pack(side="left", padx=12)
        self._reg_text(btn_val, "btn_validate")

        cols = ("sev", "cat", "item", "msg", "fix")
        self.tree_val = ttk.Treeview(self.tab_validator, columns=cols, show="headings", selectmode="browse")
        self._reg_heading(self.tree_val, "sev", "col_val_sev")
        self._reg_heading(self.tree_val, "cat", "col_val_cat")
        self._reg_heading(self.tree_val, "item", "col_val_item")
        self._reg_heading(self.tree_val, "msg", "col_val_msg")
        self._reg_heading(self.tree_val, "fix", "col_val_fix")

        self.tree_val.column("sev", width=90)
        self.tree_val.column("cat", width=130)
        self.tree_val.column("item", width=160)
        self.tree_val.column("msg", width=320)
        self.tree_val.column("fix", width=300)

        scroll = ttk.Scrollbar(self.tab_validator, orient="vertical", command=self.tree_val.yview)
        self.tree_val.configure(yscrollcommand=scroll.set)

        self.tree_val.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _setup_diff_tab(self):
        panel = ttk.Frame(self.tab_diff, style="Card.TFrame", padding=14)
        panel.pack(fill="x", pady=(0, 8))

        lbl_d_title = ttk.Label(panel, text=i18n("diff_title"), font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel")
        lbl_d_title.pack(anchor="w", pady=(0, 4))
        self._reg_text(lbl_d_title, "diff_title")

        lbl_d_desc = ttk.Label(panel, text=i18n("diff_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_d_desc.pack(anchor="w", pady=(0, 10))
        self._reg_text(lbl_d_desc, "diff_desc")

        # Map A
        f_a = ttk.Frame(panel, style="Card.TFrame")
        f_a.pack(fill="x", pady=2)
        lbl_ma = ttk.Label(f_a, text=i18n("lbl_base_map"), style="Card.TLabel", width=18)
        lbl_ma.pack(side="left")
        self._reg_text(lbl_ma, "lbl_base_map")
        self.entry_diff_a = tk.Entry(f_a, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_diff_a.pack(side="left", fill="x", expand=True, padx=6)
        btn_bra = ttk.Button(f_a, text=i18n("btn_browse"), command=self._browse_diff_a)
        btn_bra.pack(side="right")
        self._reg_text(btn_bra, "btn_browse")

        # Map B
        f_b = ttk.Frame(panel, style="Card.TFrame")
        f_b.pack(fill="x", pady=2)
        lbl_mb = ttk.Label(f_b, text=i18n("lbl_compare_map"), style="Card.TLabel", width=18)
        lbl_mb.pack(side="left")
        self._reg_text(lbl_mb, "lbl_compare_map")
        self.entry_diff_b = tk.Entry(f_b, bg="#111827", fg=self.text_color, insertbackground="white")
        self.entry_diff_b.pack(side="left", fill="x", expand=True, padx=6)
        btn_brb = ttk.Button(f_b, text=i18n("btn_browse"), command=self._browse_diff_b)
        btn_brb.pack(side="right")
        self._reg_text(btn_brb, "btn_browse")

        f_btn = ttk.Frame(panel, style="Card.TFrame")
        f_btn.pack(fill="x", pady=(8, 0))
        btn_cmp = ttk.Button(f_btn, text=i18n("btn_compare"), style="Primary.TButton", command=self._on_compare_maps)
        btn_cmp.pack(side="left", padx=4)
        self._reg_text(btn_cmp, "btn_compare")

        btn_rep = ttk.Button(f_btn, text=i18n("btn_export_diff_md"), command=self._on_save_diff_report)
        btn_rep.pack(side="left", padx=8)
        self._reg_text(btn_rep, "btn_export_diff_md")

        # Delta Cards
        self.cards_diff = ttk.Frame(self.tab_diff)
        self.cards_diff.pack(fill="x", pady=6)

        self.diff_vars = {
            "size": tk.StringVar(value="-"),
            "actors": tk.StringVar(value="-"),
            "meshes": tk.StringVar(value="-"),
            "pkgs": tk.StringVar(value="-"),
        }

        diff_cards = [
            ("card_diff_actors", "actors"),
            ("card_diff_pkgs", "pkgs"),
            ("card_diff_classes", "meshes"),
            ("card_unr_size", "size"),
        ]

        for i, (key, var_key) in enumerate(diff_cards):
            card = ttk.Frame(self.cards_diff, style="Card.TFrame", padding=10)
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            self.cards_diff.columnconfigure(i, weight=1)

            lbl = ttk.Label(card, text=i18n(key), style="MetricLbl.TLabel")
            lbl.pack(anchor="w")
            self._reg_text(lbl, key)
            ttk.Label(card, textvariable=self.diff_vars[var_key], style="MetricVal.TLabel").pack(anchor="w", pady=(3, 0))

        # Diff Treeview
        paned = ttk.PanedWindow(self.tab_diff, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(6, 0))

        # Left: Actor class breakdown
        f_left = ttk.Frame(paned, padding=4)
        cols_act = ("cls", "cnt_a", "cnt_b", "delta")
        self.tree_diff_actors = ttk.Treeview(f_left, columns=cols_act, show="headings", selectmode="browse")
        self._reg_heading(self.tree_diff_actors, "cls", "col_diff_cls")
        self._reg_heading(self.tree_diff_actors, "cnt_a", "col_diff_cnta")
        self._reg_heading(self.tree_diff_actors, "cnt_b", "col_diff_cntb")
        self._reg_heading(self.tree_diff_actors, "delta", "col_diff_delta")

        self.tree_diff_actors.column("cls", width=180)
        self.tree_diff_actors.column("cnt_a", width=75)
        self.tree_diff_actors.column("cnt_b", width=75)
        self.tree_diff_actors.column("delta", width=95)
        self.tree_diff_actors.pack(fill="both", expand=True)
        paned.add(f_left, weight=1)

        # Right: New packages & classes in Map B
        f_right = ttk.Frame(paned, padding=4)
        self.list_diff_news = tk.Listbox(f_right, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.list_diff_news.pack(fill="both", expand=True)
        paned.add(f_right, weight=1)

    def _setup_isolate_tab(self):
        header_card = ttk.Frame(self.tab_isolate, style="Card.TFrame", padding=12)
        header_card.pack(fill="x", pady=(0, 10))

        lbl_i_title = ttk.Label(header_card, text=i18n("iso_title"), font=("Segoe UI", 12, "bold"), foreground=self.accent_color, style="Card.TLabel")
        lbl_i_title.pack(anchor="w")
        self._reg_text(lbl_i_title, "iso_title")

        lbl_i_desc = ttk.Label(header_card, text=i18n("iso_desc"), style="Card.TLabel", foreground=self.text_muted)
        lbl_i_desc.pack(anchor="w", pady=(4, 0))
        self._reg_text(lbl_i_desc, "iso_desc")

        # Config Frame
        cfg_frame = ttk.Frame(self.tab_isolate, style="Card.TFrame", padding=12)
        cfg_frame.pack(fill="x", pady=6)

        r1 = ttk.Frame(cfg_frame, style="Card.TFrame")
        r1.pack(fill="x", pady=4)
        lbl_tc = ttk.Label(r1, text=i18n("lbl_iso_chronicle"), style="Card.TLabel", width=22)
        lbl_tc.pack(side="left")
        self._reg_text(lbl_tc, "lbl_iso_chronicle")
        self.combo_iso_chronicle = ttk.Combobox(r1, values=["C4 (Scions of Destiny)", "Interlude (C6)", "High Five (H5)", "Classic"], state="readonly", width=28)
        self.combo_iso_chronicle.set("Interlude (C6)")
        self.combo_iso_chronicle.pack(side="left", padx=5)

        r2 = ttk.Frame(cfg_frame, style="Card.TFrame")
        r2.pack(fill="x", pady=4)
        lbl_out = ttk.Label(r2, text=i18n("label_output"), style="Card.TLabel", width=22)
        lbl_out.pack(side="left")
        self._reg_text(lbl_out, "label_output")
        self.entry_iso_out = ttk.Entry(r2)
        self.entry_iso_out.pack(side="left", fill="x", expand=True, padx=5)
        btn_br_iso = ttk.Button(r2, text=i18n("btn_browse"), command=self._browse_iso_out)
        btn_br_iso.pack(side="left")
        self._reg_text(btn_br_iso, "btn_browse")

        # Action Buttons
        btn_frame = ttk.Frame(self.tab_isolate, style="Card.TFrame", padding=8)
        btn_frame.pack(fill="x", pady=6)
        btn_start = ttk.Button(btn_frame, text=i18n("btn_start_isolation"), style="Action.TButton", command=self._on_isolate_map)
        btn_start.pack(side="left", padx=5)
        self._reg_text(btn_start, "btn_start_isolation")

        btn_op_iso = ttk.Button(btn_frame, text=i18n("btn_open_iso_folder"), style="Primary.TButton", command=self._open_iso_output_folder)
        btn_op_iso.pack(side="left", padx=5)
        self._reg_text(btn_op_iso, "btn_open_iso_folder")

        # Metrics cards
        m_frame = ttk.Frame(self.tab_isolate, style="Card.TFrame", padding=10)
        m_frame.pack(fill="x", pady=6)

        self.iso_vars = {
            "meshes": tk.StringVar(value="-"),
            "textures": tk.StringVar(value="-"),
            "downgraded": tk.StringVar(value="-"),
            "size": tk.StringVar(value="-"),
        }

        cols = [
            ("card_iso_meshes", "meshes"),
            ("card_iso_textures", "textures"),
            ("card_iso_downgraded", "downgraded"),
            ("card_total_size", "size"),
        ]
        for key, var_key in cols:
            c = ttk.Frame(m_frame, style="Card.TFrame", padding=8)
            c.pack(side="left", expand=True, fill="both", padx=4)
            ttk.Label(c, textvariable=self.iso_vars[var_key], font=("Segoe UI", 16, "bold"), foreground=self.accent_color, style="Card.TLabel").pack()
            lbl_sub = ttk.Label(c, text=i18n(key), font=("Segoe UI", 8), foreground=self.text_muted, style="Card.TLabel")
            lbl_sub.pack()
            self._reg_text(lbl_sub, key)

        # Log & details
        det_frame = ttk.Frame(self.tab_isolate, style="Card.TFrame", padding=8)
        det_frame.pack(fill="both", expand=True, pady=6)
        self.text_iso_log = tk.Text(det_frame, bg="#182234", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.text_iso_log.pack(fill="both", expand=True, pady=4)

    def _setup_logs_tab(self):
        f_top = ttk.Frame(self.tab_logs, style="Card.TFrame", padding=6)
        f_top.pack(fill="x", pady=(0, 4))
        btn_clr = ttk.Button(f_top, text=i18n("btn_clear_logs"), command=lambda: self.txt_logs.delete("1.0", "end"))
        btn_clr.pack(side="left", padx=4)
        self._reg_text(btn_clr, "btn_clear_logs")

        self.txt_logs = tk.Text(self.tab_logs, bg="#0d1117", fg=self.text_color, font=("Consolas", 9), relief="flat")
        self.txt_logs.pack(fill="both", expand=True)

    # --- Callbacks ---
    def _log(self, msg: str):
        self.txt_logs.insert("end", msg + "\n")
        self.txt_logs.see("end")

    def _browse_unr(self):
        path = filedialog.askopenfilename(title=i18n("label_map"), filetypes=[("Unreal Maps", "*.unr"), ("All Files", "*.*")])
        if path:
            self.entry_unr.delete(0, "end")
            self.entry_unr.insert(0, path)
            p = Path(path)
            if not self.entry_output.get():
                self.entry_output.insert(0, str(p.parent / f"Export_{p.stem}"))

    def _browse_client(self):
        folder = filedialog.askdirectory(title=i18n("label_client"))
        if folder:
            self.entry_client.delete(0, "end")
            self.entry_client.insert(0, folder)

    def _browse_output(self):
        folder = filedialog.askdirectory(title=i18n("label_output"))
        if folder:
            self.entry_output.delete(0, "end")
            self.entry_output.insert(0, folder)

    def _browse_tex_folder(self):
        folder = filedialog.askdirectory(title=i18n("lbl_tex_folder"))
        if folder:
            self.entry_tex_folder.delete(0, "end")
            self.entry_tex_folder.insert(0, folder)

    def _browse_tex_out(self):
        folder = filedialog.askdirectory(title=i18n("label_output"))
        if folder:
            self.entry_tex_out.delete(0, "end")
            self.entry_tex_out.insert(0, folder)

    def _browse_utx_file(self):
        path = filedialog.askopenfilename(title=i18n("lbl_select_utx"), filetypes=[("Unreal Textures", "*.utx"), ("All Files", "*.*")])
        if path:
            self.entry_utx_target.delete(0, "end")
            self.entry_utx_target.insert(0, path)

    def _on_analyze(self):
        unr_path = self.entry_unr.get().strip()
        if not unr_path or not os.path.exists(unr_path):
            messagebox.showerror("Error", i18n("msg_select_unr"))
            return

        client_path = self.entry_client.get().strip()
        deep_scan = self.var_deep_scan.get()

        self.status_var.set(i18n("status_analyzing"))
        self.btn_analyze.config(state="disabled")

        def worker():
            try:
                self._log(f"--- Analyzing: {Path(unr_path).name} ---")
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
                self.root.after(0, lambda: messagebox.showerror("Analysis Error", str(e)))
                self.root.after(0, lambda: self._log(f"[ERROR] {e}"))
            finally:
                self.root.after(0, lambda: self.btn_analyze.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set(i18n("status_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _update_ui_with_results(self, census: MapCensus):
        res = self.analysis_result
        if not res:
            return

        self.metric_vars["size"].set(format_bytes(res.map_size))
        ver_text = f"v{res.unreal_version}"
        if res.l2_crypt_version:
            ver_text += f" (L2:{res.l2_crypt_version})"
        self.metric_vars["ver"].set(ver_text)
        self.metric_vars["meshes"].set(str(len(res.static_mesh_packages)))
        self.metric_vars["textures"].set(str(len(res.texture_packages)))
        self.metric_vars["sounds"].set(str(len(res.sound_packages)))
        self.metric_vars["missing"].set(str(len(res.missing_packages)))

        self.txt_summary.delete("1.0", "end")
        summary_text = (
            f"Map: {res.map_name}\n"
            f"Path: {res.map_path}\n"
            f"Engine Version: UE2 {res.unreal_version} | Licensee: {res.licensee_mode}\n"
            f"Names: {res.total_names} | Imports: {res.total_imports} | Exports: {res.total_exports}\n\n"
            f"Mesh Packages (.usx): {len(res.static_mesh_packages)}\n"
            f"Texture Packages (.utx): {len(res.texture_packages)}\n"
            f"Sound Packages (.uax): {len(res.sound_packages)}\n"
            f"Referenced Meshes: {len(res.static_meshes_used)}\n"
            f"Referenced Textures/Shaders: {len(res.textures_used) + len(res.shaders_used)}\n"
        )
        if res.missing_packages:
            summary_text += f"\n[WARNING] {len(res.missing_packages)} packages missing in client folder:\n"
            for m in res.missing_packages:
                summary_text += f" - {m}\n"
        self.txt_summary.insert("end", summary_text)

        # Packages TreeView
        for item in self.tree_pkgs.get_children():
            self.tree_pkgs.delete(item)

        all_pkgs = list(res.all_packages().values())
        all_pkgs.sort(key=lambda p: (p.category, p.name.lower()))
        for pkg in all_pkgs:
            status_str = "FOUND" if pkg.found else "MISSING"
            ref_mode = "Direct" if pkg.direct else "Cascade (Mesh)"
            refs = ", ".join(pkg.referenced_by) if pkg.referenced_by else "-"
            size_str = format_bytes(pkg.file_size) if pkg.found else "-"

            self.tree_pkgs.insert("", "end", values=(
                pkg.category, pkg.name, pkg.expected_extension, status_str, size_str, ref_mode, refs
            ))

        # Assets Lists
        self.list_meshes.delete(0, "end")
        for m in res.static_meshes_used:
            self.list_meshes.insert("end", m)

        self.list_textures.delete(0, "end")
        for t in res.textures_used:
            self.list_textures.insert("end", f"[Texture] {t}")
        for s in res.shaders_used:
            self.list_textures.insert("end", f"[Shader]  {s}")

        # Terrain & Actors Census
        if census.terrain:
            self.lbl_terrain_map.config(text=f"Heightmap: {census.terrain.heightmap_texture}")
            self.lbl_terrain_scale.config(text=f"Terrain Scale: X={census.terrain.terrain_scale[0]}, Y={census.terrain.terrain_scale[1]}, Z={census.terrain.terrain_scale[2]}")

        for item in self.tree_instances.get_children():
            self.tree_instances.delete(item)
        for mesh, cnt in census.static_mesh_usage.items():
            self.tree_instances.insert("", "end", values=(mesh, f"{cnt}x"))

        for item in self.tree_actors.get_children():
            self.tree_actors.delete(item)
        for cls_name, cnt in census.actor_class_counts.items():
            self.tree_actors.insert("", "end", values=(cls_name, cnt))

        self._log(f"Analysis completed for {res.map_name}: {len(res.all_packages())} packages discovered.")

    def _on_export(self):
        if not self.analysis_result:
            messagebox.showwarning("Warning", "Please analyze a map first.")
            return

        out_dir = self.entry_output.get().strip()
        if not out_dir:
            messagebox.showerror("Error", i18n("msg_select_output"))
            return

        self.status_var.set(i18n("status_exporting"))
        self.btn_export.config(state="disabled")

        def worker():
            try:
                collector = AssetCollector(target_directory=out_dir)
                summary = collector.export_dependencies(self.analysis_result)
                msg = f"Exported {len(summary.copied_files)} files ({format_bytes(summary.total_bytes_copied)})."
                if summary.missing_files:
                    msg += f"\n{len(summary.missing_files)} packages missing from client."
                self.root.after(0, lambda: messagebox.showinfo("Export Finished", msg))
                self.root.after(0, lambda: self._log(f"[EXPORT] {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Export Error", str(e)))
            finally:
                self.root.after(0, lambda: self.btn_export.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set(i18n("status_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _on_list_utx(self):
        utx_path = self.entry_utx_target.get().strip()
        if not utx_path or not os.path.exists(utx_path):
            messagebox.showerror("Error", "Please select a valid .utx package.")
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
            self._log(f"UTX {Path(utx_path).name}: {len(textures)} textures listed.")
        except Exception as e:
            messagebox.showerror("UTX Error", str(e))

    def _on_extract_utx(self):
        if not self.active_utx_extractor:
            self._on_list_utx()
        if not self.active_utx_extractor:
            return

        out_dir = filedialog.askdirectory(title="Select folder for extracted textures")
        if not out_dir:
            return

        self.status_var.set("Extracting textures...")

        def worker():
            try:
                rep = self.active_utx_extractor.extract_all(output_folder=out_dir, export_dds=True, export_png=True)
                msg = f"Extracted {rep['extracted']} of {rep['total']} textures to {out_dir}."
                self.root.after(0, lambda: messagebox.showinfo("Extraction Done", msg))
                self.root.after(0, lambda: self._log(f"[UTX] {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Extraction Error", str(e)))
            finally:
                self.root.after(0, lambda: self.status_var.set(i18n("status_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _on_start_resize(self):
        in_dir = self.entry_tex_folder.get().strip()
        out_dir = self.entry_tex_out.get().strip()
        if not in_dir or not os.path.exists(in_dir):
            messagebox.showerror("Error", "Please select a valid input texture folder.")
            return
        if not out_dir:
            out_dir = str(Path(in_dir) / "Resized")
            self.entry_tex_out.delete(0, "end")
            self.entry_tex_out.insert(0, out_dir)

        max_dim = int(self.combo_res.get())
        self.btn_resize.config(state="disabled")
        self.txt_resize_log.delete("1.0", "end")

        def prog_cb(curr, total, name):
            pct = (curr / total) * 100
            self.prog_var.set(pct)
            self.txt_resize_log.insert("end", f"[{curr}/{total}] {name}\n")
            self.txt_resize_log.see("end")

        def worker():
            try:
                rep = batch_resize_folder(in_dir, out_dir, max_dimension=max_dim, progress_callback=prog_cb)
                msg = f"Processed {rep['processed']} textures ({rep['resized']} resized, {rep['skipped']} kept)."
                self.root.after(0, lambda: messagebox.showinfo("Resize Complete", msg))
                self.root.after(0, lambda: self._log(f"[RESIZE] {msg}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Resize Error", str(e)))
            finally:
                self.root.after(0, lambda: self.btn_resize.config(state="normal"))
                self.root.after(0, lambda: self.status_var.set(i18n("status_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _on_validate_chronicle(self):
        unr_path = self.entry_unr.get().strip()
        if not unr_path or not os.path.exists(unr_path):
            messagebox.showerror("Error", i18n("msg_select_unr"))
            return

        ch_map = {
            "C4 (Scions of Destiny)": "c4",
            "Interlude (C6)": "interlude",
            "High Five (H5)": "h5",
            "Classic": "classic",
        }
        target = ch_map.get(self.combo_target_chronicle.get(), "interlude")

        for item in self.tree_val.get_children():
            self.tree_val.delete(item)

        try:
            val = ChronicleValidator()
            rep = val.validate_map(unr_path, target_chronicle=target)
            for diag in rep.diagnostics:
                self.tree_val.insert("", "end", values=(diag.severity, diag.category, diag.item_name, diag.message, diag.recommended_fix))
            self._log(f"Validation: {rep.chronicle.upper()} | Score: {rep.compatibility_score}/100 | Issues: {len(rep.diagnostics)}")
        except Exception as e:
            messagebox.showerror("Validation Error", str(e))

    def _browse_diff_a(self):
        path = filedialog.askopenfilename(title=i18n("lbl_base_map"), filetypes=[("Unreal Maps", "*.unr"), ("All Files", "*.*")])
        if path:
            self.entry_diff_a.delete(0, "end")
            self.entry_diff_a.insert(0, path)

    def _browse_diff_b(self):
        path = filedialog.askopenfilename(title=i18n("lbl_compare_map"), filetypes=[("Unreal Maps", "*.unr"), ("All Files", "*.*")])
        if path:
            self.entry_diff_b.delete(0, "end")
            self.entry_diff_b.insert(0, path)

    def _on_compare_maps(self):
        path_a = self.entry_diff_a.get().strip()
        path_b = self.entry_diff_b.get().strip()

        if not path_a or not os.path.exists(path_a):
            messagebox.showerror("Error", "Please select a valid Base Map A.")
            return
        if not path_b or not os.path.exists(path_b):
            messagebox.showerror("Error", "Please select a valid Comparison Map B.")
            return

        self.status_var.set("Comparing maps...")

        def worker():
            try:
                comp = MapComparator(path_a, path_b)
                diff = comp.compare()
                self.last_diff_result = diff

                def update():
                    d_size = (diff.map_b_size - diff.map_a_size) / (1024 * 1024)
                    self.diff_vars["size"].set(f"{'+' if d_size >= 0 else ''}{d_size:.2f} MB")
                    d_act = diff.actors_b - diff.actors_a
                    self.diff_vars["actors"].set(f"{'+' if d_act >= 0 else ''}{d_act:,}")
                    d_mesh = len(diff.meshes_b) - len(diff.meshes_a)
                    self.diff_vars["meshes"].set(f"{'+' if d_mesh >= 0 else ''}{d_mesh:,}")
                    d_pkg = len(diff.packages_b) - len(diff.packages_a)
                    self.diff_vars["pkgs"].set(f"{'+' if d_pkg >= 0 else ''}{d_pkg:,}")

                    for item in self.tree_diff_actors.get_children():
                        self.tree_diff_actors.delete(item)

                    all_classes = sorted(set(diff.class_counts_a.keys()).union(set(diff.class_counts_b.keys())))
                    for cls in all_classes:
                        ca = diff.class_counts_a.get(cls, 0)
                        cb = diff.class_counts_b.get(cls, 0)
                        delta = cb - ca
                        d_str = f"+{delta}" if delta > 0 else (str(delta) if delta < 0 else "=")
                        self.tree_diff_actors.insert("", "end", values=(cls, ca, cb, d_str))

                    self.list_diff_news.delete(0, "end")
                    self.list_diff_news.insert("end", f"=== {len(diff.classes_added)} NEW CLASSES IN MAP B ===")
                    for c in sorted(diff.classes_added):
                        self.list_diff_news.insert("end", f"  [Class] +{c}")

                    self.list_diff_news.insert("end", "")
                    self.list_diff_news.insert("end", f"=== {len(diff.packages_added)} NEW PACKAGES IN MAP B ===")
                    for p in sorted(diff.packages_added):
                        self.list_diff_news.insert("end", f"  [Package] +{p}")

                    self._log(f"Map comparison finished: {diff.map_a_name} vs {diff.map_b_name}")

                self.root.after(0, update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Comparison Error", str(e)))
            finally:
                self.root.after(0, lambda: self.status_var.set(i18n("status_ready")))

        threading.Thread(target=worker, daemon=True).start()

    def _on_save_diff_report(self):
        if not self.last_diff_result:
            messagebox.showwarning("Warning", "Please run map comparison first.")
            return

        out_path = filedialog.asksaveasfilename(
            title=i18n("btn_export_diff_md"),
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")]
        )
        if out_path:
            comp = MapComparator(self.last_diff_result.map_a_name, self.last_diff_result.map_b_name)
            md = comp.generate_markdown_report(self.last_diff_result)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(md)
            messagebox.showinfo("Saved", f"Report saved to:\n{out_path}")

    def _browse_iso_out(self):
        d = filedialog.askdirectory(title="Select folder for autonomous bundle")
        if d:
            self.entry_iso_out.delete(0, "end")
            self.entry_iso_out.insert(0, d)

    def _open_iso_output_folder(self):
        out_d = self.entry_iso_out.get().strip()
        if out_d and os.path.exists(out_d):
            os.startfile(out_d)
        else:
            messagebox.showinfo("Folder", "Output folder has not been created yet.")

    def _on_isolate_map(self):
        unr_path = self.entry_unr.get().strip()
        client_dir = self.entry_client.get().strip()

        if not unr_path or not os.path.exists(unr_path):
            messagebox.showerror("Error", i18n("msg_select_unr"))
            return
        if not client_dir or not os.path.exists(client_dir):
            messagebox.showerror("Error", i18n("msg_select_client"))
            return

        out_d = self.entry_iso_out.get().strip()
        if not out_d:
            stem = Path(unr_path).stem
            out_d = str(Path(unr_path).parent / f"Isolated_{stem}")
            self.entry_iso_out.delete(0, "end")
            self.entry_iso_out.insert(0, out_d)

        ch_map = {
            "C4 (Scions of Destiny)": "c4",
            "Interlude (C6)": "interlude",
            "High Five (H5)": "h5",
            "Classic": "classic",
        }
        target_ch = ch_map.get(self.combo_iso_chronicle.get(), "interlude")

        self.status_var.set(i18n("status_isolating"))
        self.text_iso_log.delete("1.0", "end")
        self.text_iso_log.insert("end", f"Starting Single-Package Transmigration for {Path(unr_path).name}...\n")
        self.text_iso_log.insert("end", f"Target Chronicle: {target_ch.upper()}\n\n")

        def worker():
            try:
                isolator = MapIsolator(client_root=client_dir)
                res = isolator.isolate_map(
                    unr_path=unr_path,
                    output_dir=out_d,
                    target_chronicle=target_ch,
                )

                def update():
                    self.iso_vars["meshes"].set(f"{res.usx_report.total_meshes_bundled:,}")
                    self.iso_vars["textures"].set(f"{res.utx_report.total_textures_bundled:,}")
                    self.iso_vars["downgraded"].set(f"{len(res.remap_report.classes_downgraded)}")
                    tot_mb = (res.remap_report.file_size_after + res.usx_report.file_size_bytes + res.utx_report.file_size_bytes) / (1024 * 1024)
                    self.iso_vars["size"].set(f"{tot_mb:.2f} MB")

                    self.text_iso_log.insert("end", f"[SUCCESS] Process completed in {res.elapsed_seconds:.2f} seconds!\n\n")
                    self.text_iso_log.insert("end", f"Generated bundle files in {res.output_dir}:\n")
                    self.text_iso_log.insert("end", f"  * Maps/{res.remapped_unr_path.name} ({res.remap_report.file_size_after / (1024*1024):.2f} MB)\n")
                    self.text_iso_log.insert("end", f"  * StaticMeshes/{res.consolidated_usx_path.name} ({res.usx_report.file_size_bytes / (1024*1024):.2f} MB)\n")
                    self.text_iso_log.insert("end", f"  * Textures/{res.consolidated_utx_path.name} ({res.utx_report.file_size_bytes / (1024*1024):.2f} MB)\n\n")
                    self.text_iso_log.insert("end", f"External packages eliminated: {len(res.remap_report.old_packages_replaced)} unified.\n")
                    if res.remap_report.classes_downgraded:
                        self.text_iso_log.insert("end", "Downgraded modern engine classes:\n")
                        for o, r in res.remap_report.classes_downgraded.items():
                            self.text_iso_log.insert("end", f"  - {o} -> {r}\n")

                    self._log(f"Single-package isolation completed: {Path(unr_path).name} in {out_d}")
                    messagebox.showinfo("Isolation Complete", f"Map successfully isolated into 3 autonomous files:\n\nFolder: {res.output_dir}")

                self.root.after(0, update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Isolation Error", str(e)))
            finally:
                self.root.after(0, lambda: self.status_var.set(i18n("status_ready")))

        threading.Thread(target=worker, daemon=True).start()

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
            messagebox.showinfo("Report", "No HTML report generated yet. Please analyze a map first.")

    def _open_output_folder(self):
        out_dir = self.entry_output.get().strip()
        if out_dir and os.path.exists(out_dir):
            os.startfile(out_d)
        else:
            messagebox.showinfo("Folder", "Output folder does not exist yet.")


def main():
    root = tk.Tk()
    app = UNRToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
