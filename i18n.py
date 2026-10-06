#!/usr/bin/env python3
"""
Internationalization (i18n) Module for UNR Tool
Provides bilingual dictionary and localization helpers for English (EN) and Russian (RU).
"""

from __future__ import annotations
from typing import Dict, Any

LANGUAGES = {
    "en": "English",
    "ru": "Русский",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # App Header & Meta
        "app_title": "UNR Dependency & Downporting Toolkit v1.7",
        "header_title": "UNR Dependency & Downporting Toolkit",
        "header_subtitle": "Lineage 2 / Unreal Engine 2 Map Transmigration Suite",
        "lang_switch_btn": "🇷🇺 Русский",
        "lang_active_lbl": "Language: English",

        # Global Input Panel
        "label_map": "Map (.UNR):",
        "label_client": "L2 Client Root:",
        "label_output": "Output Folder:",
        "btn_browse": "Browse...",
        "chk_deep_scan": "Deep Scan (.usx -> textures)",
        "btn_analyze": "🔍 Analyze Map",
        "btn_export": "📦 Export Dependencies",
        "btn_open_html": "🌐 Open HTML Report",
        "btn_open_folder": "📁 Open Folder",

        # Tabs
        "tab_summary": "📊 Summary & Metrics",
        "tab_packages": "📦 Required Packages",
        "tab_assets": "🎨 Meshes & Textures",
        "tab_terrain": "🏔️ Terrain & Actors",
        "tab_utx": "🖼️ UTX Extractor",
        "tab_textures": "⚡ Texture Resize",
        "tab_validator": "🛡️ Chronicle Validator",
        "tab_diff": "🔄 Map Comparator (Diff)",
        "tab_isolate": "📦 Autonomous Isolator (1/Class)",
        "tab_logs": "📜 Execution Logs",

        # Tab 1: Summary
        "card_sector": "SECTOR",
        "card_total_assets": "TOTAL ASSETS",
        "card_packages": "PACKAGES",
        "card_unr_size": "MAP SIZE",
        "card_total_size": "TOTAL SIZE",
        "sec_distribution": "Asset Distribution by Category",
        "sec_engine_classes": "Unique Engine Classes in Sector",
        "col_category": "Category",
        "col_count": "Asset Count",
        "col_class": "Engine Class",

        # Tab 2: Packages
        "col_pkg_name": "Package",
        "col_pkg_type": "Type",
        "col_pkg_objs": "Referenced Objects",
        "col_pkg_size": "File Size",
        "col_pkg_status": "Status",
        "col_pkg_path": "Full Path",
        "col_pkg_ext": "Ext",
        "col_pkg_refmode": "Ref Type",
        "col_pkg_refs": "Referenced By",

        # Tab 3: Detailed Assets
        "col_asset_pkg": "Package",
        "col_asset_name": "Asset Name",
        "col_asset_type": "Class / Type",
        "col_asset_status": "Status",
        "lbl_used_meshes": "Static Meshes Used:",
        "lbl_used_textures": "Textures & Shaders Used:",

        # Tab 4: Terrain & Actors
        "terrain_title": "Terrain & Actor Census Inspector",
        "terrain_desc": "Inspects TerrainInfo heightmap, scaling factors, and counts all Actor instances in the UNR package.",
        "btn_inspect_terrain": "🔍 Inspect Map Actors & Terrain",
        "card_actors_total": "TOTAL ACTORS",
        "card_actors_meshes": "STATIC MESH ACTORS",
        "card_actors_lights": "LIGHTS",
        "card_actors_terrains": "TERRAIN INFOS",
        "card_actors_emitters": "EMITTERS / FX",
        "card_actors_sounds": "AMBIENT SOUNDS",
        "lbl_heightmap": "Heightmap Texture:",
        "lbl_terrain_scale": "Terrain Scaling (X, Y, Z):",
        "col_actor_class": "Actor Class",
        "col_instance_count": "Instance Count",
        "col_mesh_name": "3D Mesh Model",
        "col_mesh_count": "Placements Count",
        "col_actor_total": "Total Actors",

        # Tab 5: UTX Extractor
        "utx_title": "Native UTX Texture Extractor",
        "utx_desc": "Extract DXT1/3/5, RGBA8, and G16 textures directly from .utx packages into DDS and PNG without external tools.",
        "lbl_select_utx": "Select UTX Package:",
        "chk_export_dds": "Export DDS (raw GPU textures)",
        "chk_export_png": "Export PNG (converted 32-bit preview)",
        "btn_extract_utx": "⚡ Extract Textures",
        "btn_list_utx": "🔍 List Textures",
        "btn_extract_all_utx": "💾 Extract All to DDS/PNG",
        "card_utx_found": "TEXTURES FOUND",
        "card_utx_extracted": "EXTRACTED",
        "card_utx_failed": "FAILED",
        "col_utx_tex": "Texture",
        "col_utx_cls": "Class",
        "col_utx_dim": "Dimensions",
        "col_utx_fmt": "Format",
        "col_utx_mips": "Mipmaps",
        "col_utx_sz": "Serial Size",

        # Tab 6: Texture Optimizer
        "tex_title": "Batch Texture Resizer & Downscaler",
        "tex_desc": "Batch downscale high-resolution textures to 1024, 512, or 256 for older game clients and low-spec systems.",
        "lbl_tex_folder": "Texture Folder:",
        "lbl_max_dim": "Max Dimension:",
        "chk_pot": "Enforce Power-of-Two (POT) dimensions",
        "btn_downscale": "📉 Downscale Textures",

        # Tab 7: Chronicle Validator
        "val_title": "Cross-Chronicle Compatibility Validator",
        "val_desc": "Checks engine classes and package versions against client limits (C4, Interlude, H5, Classic).",
        "lbl_target_chronicle": "Target Chronicle:",
        "btn_validate": "🛡️ Validate Compatibility",
        "status_compatible": "COMPATIBLE",
        "status_warning": "WARNINGS DETECTED",
        "status_incompatible": "INCOMPATIBLE",
        "col_val_sev": "Severity",
        "col_val_cat": "Category",
        "col_val_item": "Element",
        "col_val_msg": "Diagnostics",
        "col_val_fix": "Recommended Fix",

        # Tab 8: Map Diff
        "diff_title": "Cross-Chronicle Map Comparator (Diff)",
        "diff_desc": "Side-by-side comparative diffing between maps across chronicles to detect new classes, meshes, and textures.",
        "lbl_base_map": "Base Map (.UNR):",
        "lbl_compare_map": "Comparison Map (.UNR):",
        "btn_compare": "🔄 Compare Maps",
        "btn_export_diff_md": "💾 Export Markdown Report",
        "card_diff_actors": "ACTOR DELTA",
        "card_diff_pkgs": "PACKAGE DELTA",
        "card_diff_classes": "NEW CLASSES",
        "col_diff_cls": "Actor Class",
        "col_diff_cnta": "Map A",
        "col_diff_cntb": "Map B",
        "col_diff_delta": "Difference",

        # Tab 9: Autonomous Isolator
        "iso_title": "Autonomous Single-Package Isolator (1 File / Class)",
        "iso_desc": "Bundles all static meshes into 1 USX, all textures into 1 UTX, and remaps the UNR for zero conflicts across chronicles.",
        "lbl_iso_chronicle": "Target Chronicle Profile:",
        "lbl_iso_max_res": "Max Texture Resolution:",
        "chk_encrypt_111": "Encrypt Game Ready (L2Ver111/121)",
        "btn_start_isolation": "🚀 Start Isolation & Transmigration",
        "btn_open_iso_folder": "📂 Open Output Folder",
        "card_iso_chronicle": "TARGET CHRONICLE",
        "card_iso_meshes": "MESHES BUNDLED",
        "card_iso_textures": "TEXTURES BUNDLED",
        "card_iso_downgraded": "CLASSES DOWNGRADED",

        # Tab 10: Logs
        "btn_clear_logs": "🧹 Clear Logs",
        "btn_save_logs": "💾 Save Logs...",

        # Status & Messages
        "status_ready": "Ready.",
        "status_analyzing": "Analyzing map dependencies...",
        "status_exporting": "Exporting package dependencies...",
        "status_isolating": "Isolating and bundling assets into single packages...",
        "status_done": "Done!",
        "msg_select_unr": "Please select a valid .unr map file first.",
        "msg_select_client": "Please select a valid game client folder.",
        "msg_select_output": "Please select an output folder.",
    },

    "ru": {
        # App Header & Meta
        "app_title": "UNR Dependency & Downporting Toolkit v1.7",
        "header_title": "Инструментарий анализа и даунпорта карт UNR",
        "header_subtitle": "Комплекс трансмиграции и изоляции карт Lineage 2 / Unreal Engine 2",
        "lang_switch_btn": "🇺🇸 English",
        "lang_active_lbl": "Язык: Русский",

        # Global Input Panel
        "label_map": "Файл карты (.UNR):",
        "label_client": "Корень клиента L2:",
        "label_output": "Папка назначения:",
        "btn_browse": "Обзор...",
        "chk_deep_scan": "Глубокое сканирование (.usx -> текстуры)",
        "btn_analyze": "🔍 Анализ карты",
        "btn_export": "📦 Экспорт зависимостей",
        "btn_open_html": "🌐 Открыть HTML-отчет",
        "btn_open_folder": "📁 Открыть папку",

        # Tabs
        "tab_summary": "📊 Сводка и метрики",
        "tab_packages": "📦 Требуемые пакеты",
        "tab_assets": "🎨 Модели и текстуры",
        "tab_terrain": "🏔️ Ландшафт и акторы",
        "tab_utx": "🖼️ Экстрактор UTX",
        "tab_textures": "⚡ Оптимизация текстур",
        "tab_validator": "🛡️ Валидатор хроник",
        "tab_diff": "🔄 Сравнение карт (Diff)",
        "tab_isolate": "📦 Автономный изолятор (1/Класс)",
        "tab_logs": "📜 Журнал событий",

        # Tab 1: Summary
        "card_sector": "СЕКТОР",
        "card_total_assets": "ВСЕГО АССЕТОВ",
        "card_packages": "ПАКЕТОВ",
        "card_unr_size": "РАЗМЕР КАРТЫ",
        "card_total_size": "ОБЩИЙ РАЗМЕР",
        "sec_distribution": "Распределение ассетов по категориям",
        "sec_engine_classes": "Уникальные классы движка в секторе",
        "col_category": "Категория",
        "col_count": "Количество",
        "col_class": "Класс движка",

        # Tab 2: Packages
        "col_pkg_name": "Пакет",
        "col_pkg_type": "Тип",
        "col_pkg_objs": "Объектов",
        "col_pkg_size": "Размер файла",
        "col_pkg_status": "Статус",
        "col_pkg_path": "Полный путь",
        "col_pkg_ext": "Расш.",
        "col_pkg_refmode": "Тип ссылки",
        "col_pkg_refs": "Кем ссылается",

        # Tab 3: Detailed Assets
        "col_asset_pkg": "Пакет",
        "col_asset_name": "Имя ассета",
        "col_asset_type": "Класс / Тип",
        "col_asset_status": "Статус",
        "lbl_used_meshes": "Используемые статические модели (StaticMeshes):",
        "lbl_used_textures": "Используемые текстуры и шейдеры:",

        # Tab 4: Terrain & Actors
        "terrain_title": "Инспектор ландшафта и акторов",
        "terrain_desc": "Извлечение карты высот TerrainInfo, коэффициентов масштабирования и полный пересчет всех акторов в UNR.",
        "btn_inspect_terrain": "🔍 Инспектировать акторы и ландшафт",
        "card_actors_total": "ВСЕГО АКТОРОВ",
        "card_actors_meshes": "СТАТИЧЕСКИХ МОДЕЛЕЙ",
        "card_actors_lights": "ИСТОЧНИКОВ СВЕТА",
        "card_actors_terrains": "СЕКТОРОВ ЛАНДШАФТА",
        "card_actors_emitters": "ЭМИТТЕРОВ И ЭФФЕКТОВ",
        "card_actors_sounds": "ЗВУКОВЫХ ЗОН",
        "lbl_heightmap": "Текстура карты высот:",
        "lbl_terrain_scale": "Масштаб ландшафта (X, Y, Z):",
        "col_actor_class": "Класс актора",
        "col_instance_count": "Количество экземпляров",
        "col_mesh_name": "3D Модель",
        "col_mesh_count": "Количество размещений",
        "col_actor_total": "Всего акторов",

        # Tab 5: UTX Extractor
        "utx_title": "Встроенный экстрактор текстур UTX",
        "utx_desc": "Извлечение текстур DXT1/3/5, RGBA8 и G16 из файлов .utx напрямую в DDS и PNG без сторонних утилит.",
        "lbl_select_utx": "Выберите пакет UTX:",
        "chk_export_dds": "Экспорт DDS (исходные текстуры GPU)",
        "chk_export_png": "Экспорт PNG (сконвертированный 32-битный просмотр)",
        "btn_extract_utx": "⚡ Извлечь текстуры",
        "btn_list_utx": "🔍 Список текстур",
        "btn_extract_all_utx": "💾 Извлечь все в DDS/PNG",
        "card_utx_found": "ТЕКСТУР НАЙДЕНО",
        "card_utx_extracted": "ИЗВЛЕЧЕНО",
        "card_utx_failed": "ОШИБОК",
        "col_utx_tex": "Текстура",
        "col_utx_cls": "Класс",
        "col_utx_dim": "Разрешение",
        "col_utx_fmt": "Формат",
        "col_utx_mips": "Мипмапы",
        "col_utx_sz": "Размер",

        # Tab 6: Texture Optimizer
        "tex_title": "Пакетное масштабирование и сжатие текстур",
        "tex_desc": "Пакетное уменьшение текстур до 1024, 512 или 256 для слабых ПК и старых хроник (C4/Interlude).",
        "lbl_tex_folder": "Папка с текстурами:",
        "lbl_max_dim": "Макс. разрешение:",
        "chk_pot": "Принудительно кратно двум (POT: 256, 512, 1024)",
        "btn_downscale": "📉 Масштабировать текстуры",

        # Tab 7: Chronicle Validator
        "val_title": "Валидатор совместимости хроник",
        "val_desc": "Проверка классов движка и версий пакетов по ограничениям библиотек DLL (C4, Interlude, H5, Classic).",
        "lbl_target_chronicle": "Целевая хроника:",
        "btn_validate": "🛡️ Проверить совместимость",
        "status_compatible": "СОВМЕСТИМО",
        "status_warning": "ОБНАРУЖЕНЫ ПРЕДУПРЕЖДЕНИЯ",
        "status_incompatible": "НЕСОВМЕСТИМО",
        "col_val_sev": "Важность",
        "col_val_cat": "Категория",
        "col_val_item": "Элемент",
        "col_val_msg": "Диагностика",
        "col_val_fix": "Рекомендованное исправление",

        # Tab 8: Map Diff
        "diff_title": "Сравнение карт разных хроник (Diff)",
        "diff_desc": "Попарное сравнительное сопоставление карт для обнаружения новых классов, моделей и текстур между хрониками.",
        "lbl_base_map": "Базовая карта (.UNR):",
        "lbl_compare_map": "Сравниваемая карта (.UNR):",
        "btn_compare": "🔄 Сравнить карты",
        "btn_export_diff_md": "💾 Экспорт отчета в MD",
        "card_diff_actors": "РАЗНИЦА АКТОРОВ",
        "card_diff_pkgs": "РАЗНИЦА ПАКЕТОВ",
        "card_diff_classes": "НОВЫХ КЛАССОВ",
        "col_diff_cls": "Класс актора",
        "col_diff_cnta": "Карта A",
        "col_diff_cntb": "Карта B",
        "col_diff_delta": "Разница",

        # Tab 9: Autonomous Isolator
        "iso_title": "Автономный изолятор пакетов (1 файл на класс)",
        "iso_desc": "Объединяет все модели в 1 USX, все текстуры в 1 UTX и перенаправляет UNR для полной совместимости без конфликтов.",
        "lbl_iso_chronicle": "Профиль целевой хроники:",
        "lbl_iso_max_res": "Макс. разрешение текстур:",
        "chk_encrypt_111": "Шифровать для игры (L2Ver111/121)",
        "btn_start_isolation": "🚀 Запустить изоляцию и трансмиграцию",
        "btn_open_iso_folder": "📂 Открыть папку назначения",
        "card_iso_chronicle": "ЦЕЛЕВАЯ ХРОНИКА",
        "card_iso_meshes": "УПАКОВАНО МОДЕЛЕЙ",
        "card_iso_textures": "УПАКОВАНО ТЕКСТУР",
        "card_iso_downgraded": "ПОНИЖЕНО КЛАССОВ",

        # Tab 10: Logs
        "btn_clear_logs": "🧹 Очистить журнал",
        "btn_save_logs": "💾 Сохранить журнал...",

        # Status & Messages
        "status_ready": "Готов к работе.",
        "status_analyzing": "Выполняется анализ зависимостей карты...",
        "status_exporting": "Выполняется экспорт требуемых пакетов...",
        "status_isolating": "Выполняется изоляция и объединение в единые пакеты...",
        "status_done": "Завершено!",
        "msg_select_unr": "Пожалуйста, выберите корректный файл карты .unr.",
        "msg_select_client": "Пожалуйста, укажите папку клиента Lineage 2.",
        "msg_select_output": "Пожалуйста, выберите папку назначения.",
    }
}


class I18nManager:
    """Manages active language and returns translated strings."""

    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang if default_lang in TRANSLATIONS else "en"

    def set_language(self, lang: str):
        if lang in TRANSLATIONS:
            self.current_lang = lang

    def get(self, key: str, default: str = "") -> str:
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        if key in lang_dict:
            return lang_dict[key]
        return TRANSLATIONS["en"].get(key, default or key)

    def __call__(self, key: str, default: str = "") -> str:
        return self.get(key, default)


# Global singleton instance
i18n = I18nManager(default_lang="en")
