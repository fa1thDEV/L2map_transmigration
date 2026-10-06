#!/usr/bin/env python3
"""
Manifest & Report Generator for UNR Tool
Produces machine-readable JSON manifests and visual HTML / Markdown reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from unr_analyzer import MapAnalysisResult


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.2f} KB"
    else:
        return f"{b / (1024 * 1024):.2f} MB"


class ManifestGenerator:
    """Generates manifests and reports for map analysis results."""

    def __init__(self, analysis: MapAnalysisResult):
        self.res = analysis

    def to_dict(self) -> Dict[str, Any]:
        res = self.res
        return {
            "map_name": res.map_name,
            "map_path": str(res.map_path),
            "map_size_bytes": res.map_size,
            "map_size_formatted": format_bytes(res.map_size),
            "unreal_version": res.unreal_version,
            "licensee_mode": res.licensee_mode,
            "l2_crypt_version": res.l2_crypt_version,
            "metrics": {
                "total_names": res.total_names,
                "total_imports": res.total_imports,
                "total_exports": res.total_exports,
                "static_meshes_used_count": len(res.static_meshes_used),
                "textures_used_count": len(res.textures_used),
                "shaders_used_count": len(res.shaders_used),
                "sounds_used_count": len(res.sounds_used),
            },
            "packages": {
                cat: [
                    {
                        "name": pkg.name,
                        "extension": pkg.expected_extension,
                        "found": pkg.found,
                        "file_size_bytes": pkg.file_size,
                        "file_size_formatted": format_bytes(pkg.file_size),
                        "direct": pkg.direct,
                        "referenced_by": pkg.referenced_by,
                        "imported_assets_count": len(pkg.imported_assets),
                    }
                    for pkg in pkgs.values()
                ]
                for cat, pkgs in [
                    ("StaticMeshes", res.static_mesh_packages),
                    ("Textures", res.texture_packages),
                    ("Sounds", res.sound_packages),
                    ("Animations", res.animation_packages),
                    ("Scripts", res.script_packages),
                    ("Other", res.other_packages),
                ]
            },
            "missing_packages": res.missing_packages,
            "static_meshes": res.static_meshes_used,
            "textures": res.textures_used,
            "shaders": res.shaders_used,
            "sounds": res.sounds_used,
        }

    def save_json(self, output_file: Path | str) -> Path:
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return out

    def save_markdown(self, output_file: Path | str) -> Path:
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        res = self.res

        lines = [
            f"# Analysis Report: {res.map_name}",
            "",
            "## Map Summary",
            f"- **File:** `{res.map_path}`",
            f"- **Size:** {format_bytes(res.map_size)}",
            f"- **Unreal Engine Version:** {res.unreal_version} (Licensee: {res.licensee_mode})",
            f"- **Encryption Header:** Lineage2Ver{res.l2_crypt_version}" if res.l2_crypt_version else "- **Encryption Header:** None / Raw UE2",
            f"- **Names:** {res.total_names} | **Imports:** {res.total_imports} | **Exports:** {res.total_exports}",
            f"- **Assets Used:** {len(res.static_meshes_used)} Meshes, {len(res.textures_used)} Textures, {len(res.shaders_used)} Shaders, {len(res.sounds_used)} Sounds",
            "",
            "## Required Packages",
            "",
            "| Category | Package | Extension | Status | Size | Direct? | Referenced By |",
            "| :--- | :--- | :--- | :---: | ---: | :---: | :--- |",
        ]

        for cat, pkgs in [
            ("StaticMeshes", res.static_mesh_packages),
            ("Textures", res.texture_packages),
            ("Sounds", res.sound_packages),
            ("Animations", res.animation_packages),
            ("Scripts", res.script_packages),
        ]:
            for pkg in sorted(pkgs.values(), key=lambda x: x.name.lower()):
                status = "FOUND" if pkg.found else "MISSING"
                direct = "Yes" if pkg.direct else "Cascaded (Mesh)"
                refs = ", ".join(pkg.referenced_by) if pkg.referenced_by else "-"
                size_str = format_bytes(pkg.file_size) if pkg.found else "-"
                lines.append(f"| {cat} | `{pkg.name}` | `{pkg.expected_extension}` | {status} | {size_str} | {direct} | {refs} |")

        if res.missing_packages:
            lines.extend([
                "",
                "## Missing Packages",
                "The following packages are referenced by the map but were not found in the client:",
            ])
            for m in res.missing_packages:
                lines.append(f"- `{m}`")

        lines.extend([
            "",
            "## Imported Static Meshes (Top 30)",
        ])
        for mesh in res.static_meshes_used[:30]:
            lines.append(f"- `{mesh}`")
        if len(res.static_meshes_used) > 30:
            lines.append(f"- *...and {len(res.static_meshes_used) - 30} more*")

        lines.extend([
            "",
            "## Imported Textures & Shaders (Top 30)",
        ])
        for tex in (res.textures_used + res.shaders_used)[:30]:
            lines.append(f"- `{tex}`")
        if len(res.textures_used + res.shaders_used) > 30:
            lines.append(f"- *...and {len(res.textures_used + res.shaders_used) - 30} more*")

        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return out

    def save_html(self, output_file: Path | str) -> Path:
        out = Path(output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        res = self.res

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Map Analysis Report - {res.map_name}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-glow: rgba(56, 189, 248, 0.2);
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --border: #334155;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 30px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .header {{
      background: var(--card-bg);
      padding: 24px 30px;
      border-radius: 12px;
      border: 1px solid var(--border);
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 15px;
    }}
    .header h1 {{ font-size: 26px; color: var(--accent); }}
    .header .subtitle {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge-found {{ background: rgba(34, 197, 94, 0.15); color: var(--success); border: 1px solid var(--success); }}
    .badge-missing {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }}
    .badge-direct {{ background: rgba(56, 189, 248, 0.15); color: var(--accent); }}
    .badge-cascade {{ background: rgba(245, 158, 11, 0.15); color: var(--warning); }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .card {{
      background: var(--card-bg);
      padding: 20px;
      border-radius: 10px;
      border: 1px solid var(--border);
    }}
    .card .label {{ color: var(--text-muted); font-size: 13px; text-transform: uppercase; font-weight: 600; }}
    .card .value {{ font-size: 24px; font-weight: 700; color: var(--text); margin-top: 6px; }}

    .section {{
      background: var(--card-bg);
      padding: 24px;
      border-radius: 10px;
      border: 1px solid var(--border);
      margin-bottom: 24px;
    }}
    .section h2 {{ font-size: 18px; margin-bottom: 16px; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 10px; }}

    table {{ width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }}
    th, td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); }}
    th {{ background: rgba(15, 23, 42, 0.6); color: var(--text-muted); font-size: 12px; text-transform: uppercase; }}
    tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}

    .asset-list {{
      max-height: 250px;
      overflow-y: auto;
      background: #090d16;
      padding: 12px;
      border-radius: 6px;
      font-family: monospace;
      font-size: 12px;
      border: 1px solid var(--border);
    }}
    .asset-list div {{ padding: 3px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1>Map Dependency Report</h1>
        <div class="subtitle">{res.map_name} &bull; {res.map_path}</div>
      </div>
      <div>
        <span class="badge badge-direct">UE2 Version {res.unreal_version}</span>
        <span class="badge badge-cascade">Licensee {res.licensee_mode}</span>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="label">Map File Size</div>
        <div class="value">{format_bytes(res.map_size)}</div>
      </div>
      <div class="card">
        <div class="label">StaticMesh Packages</div>
        <div class="value">{len(res.static_mesh_packages)}</div>
      </div>
      <div class="card">
        <div class="label">Texture Packages</div>
        <div class="value">{len(res.texture_packages)}</div>
      </div>
      <div class="card">
        <div class="label">Sound Packages</div>
        <div class="value">{len(res.sound_packages)}</div>
      </div>
      <div class="card">
        <div class="label">3D Meshes Used</div>
        <div class="value">{len(res.static_meshes_used)}</div>
      </div>
      <div class="card">
        <div class="label">Textures & Shaders</div>
        <div class="value">{len(res.textures_used) + len(res.shaders_used)}</div>
      </div>
    </div>

    <div class="section">
      <h2>Required Packages Breakdown</h2>
      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Package Name</th>
            <th>Extension</th>
            <th>Status</th>
            <th>Size</th>
            <th>Reference Mode</th>
            <th>Referenced By</th>
          </tr>
        </thead>
        <tbody>
"""

        all_pkgs = list(res.all_packages().values())
        all_pkgs.sort(key=lambda p: (p.category, p.name.lower()))
        for pkg in all_pkgs:
            status_badge = f'<span class="badge badge-found">Found</span>' if pkg.found else f'<span class="badge badge-missing">Missing</span>'
            ref_badge = f'<span class="badge badge-direct">Direct</span>' if pkg.direct else f'<span class="badge badge-cascade">Mesh Cascaded</span>'
            ref_by = ", ".join(pkg.referenced_by) if pkg.referenced_by else "-"
            size_str = format_bytes(pkg.file_size) if pkg.found else "-"

            html += f"""          <tr>
            <td><strong>{pkg.category}</strong></td>
            <td><code>{pkg.name}</code></td>
            <td><code>{pkg.expected_extension}</code></td>
            <td>{status_badge}</td>
            <td>{size_str}</td>
            <td>{ref_badge}</td>
            <td style="color: var(--text-muted); font-size: 12px;">{ref_by}</td>
          </tr>
"""

        html += f"""        </tbody>
      </table>
    </div>

    <div class="grid" style="grid-template-columns: 1fr 1fr;">
      <div class="section">
        <h2>Static Meshes Referencing ({len(res.static_meshes_used)})</h2>
        <div class="asset-list">
"""
        for m in res.static_meshes_used:
            html += f"          <div>{m}</div>\n"
        html += """        </div>
      </div>

      <div class="section">
        <h2>Textures & Shaders ({len(res.textures_used) + len(res.shaders_used)})</h2>
        <div class="asset-list">
"""
        for t in res.textures_used:
            html += f"          <div style='color: #38bdf8;'>[Texture] {t}</div>\n"
        for s in res.shaders_used:
            html += f"          <div style='color: #a855f7;'>[Shader] {s}</div>\n"
        html += """        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        return out
