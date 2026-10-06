#!/usr/bin/env python3
"""
Map Terrain & Actor Inspector for UNR Tool
Analyzes TerrainInfo actors, heightmaps, texture layers, and StaticMesh actor placements.
"""

from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ue2_package import UE2Package, read_compact_index


@dataclass
class TerrainLayerInfo:
    texture_name: str
    alpha_map_name: str
    u_scale: float = 1.0
    v_scale: float = 1.0


@dataclass
class TerrainData:
    actor_name: str
    heightmap_texture: str
    terrain_scale: Tuple[float, float, float] = (64.0, 64.0, 16.0)
    layers: List[TerrainLayerInfo] = field(default_factory=list)


@dataclass
class MapCensus:
    map_name: str
    total_actors: int
    actor_class_counts: Dict[str, int] = field(default_factory=dict)
    static_mesh_usage: Dict[str, int] = field(default_factory=dict)
    terrain: Optional[TerrainData] = None


class MapInspector:
    """Inspects actor placements, terrain data, and mesh usage within a .unr map."""

    def __init__(self, map_package: UE2Package):
        self.pkg = map_package

    @classmethod
    def load_from_file(cls, map_path: Path | str) -> MapInspector:
        pkg = UE2Package.load_from_file(map_path)
        return cls(pkg)

    def inspect(self) -> MapCensus:
        census = MapCensus(
            map_name=self.pkg.filename,
            total_actors=len(self.pkg.exports),
        )

        class_counter = Counter()
        mesh_counter = Counter()

        for exp in self.pkg.exports:
            cls_name = self._resolve_class_name(exp.class_index)
            class_counter[cls_name] += 1

            if cls_name.lower() == "staticmeshactor":
                mesh_ref = self._extract_static_mesh_prop(exp)
                if mesh_ref:
                    mesh_counter[mesh_ref] += 1
            elif cls_name.lower() in ("terraininfo", "terrainsector") and not census.terrain:
                census.terrain = self._extract_terrain_info(exp)

        census.actor_class_counts = dict(class_counter.most_common())
        census.static_mesh_usage = dict(mesh_counter.most_common())
        return census

    def _resolve_class_name(self, class_idx: int) -> str:
        if class_idx < 0:
            imp_idx = -class_idx - 1
            if 0 <= imp_idx < len(self.pkg.imports):
                return self.pkg.imports[imp_idx].object_name
        elif class_idx > 0:
            exp_idx = class_idx - 1
            if 0 <= exp_idx < len(self.pkg.exports):
                return self.pkg.exports[exp_idx].object_name
        return "Unknown"

    def _resolve_object_ref(self, obj_idx: int) -> str:
        if obj_idx < 0:
            imp_idx = -obj_idx - 1
            if 0 <= imp_idx < len(self.pkg.imports):
                return self.pkg.imports[imp_idx].full_path
        elif obj_idx > 0:
            exp_idx = obj_idx - 1
            if 0 <= exp_idx < len(self.pkg.exports):
                return self.pkg.exports[exp_idx].object_name
        return ""

    def _extract_static_mesh_prop(self, exp) -> Optional[str]:
        """Extracts the StaticMesh property reference from a StaticMeshActor export."""
        buf = self.pkg.raw_data
        pos = exp.serial_offset
        end_pos = pos + exp.serial_size

        try:
            while pos < end_pos:
                name_idx, pos = read_compact_index(buf, pos)
                pname = self.pkg.names[name_idx] if 0 <= name_idx < len(self.pkg.names) else ""
                if pname == "None":
                    break

                if pos >= end_pos:
                    break
                info = buf[pos]
                pos += 1
                ptype = info & 0x0F
                psize_type = (info >> 4) & 0x07
                is_array = (info >> 7) & 0x01

                if ptype == 3:  # Boolean property has 0 data bytes
                    size = 0
                elif psize_type == 0: size = 1
                elif psize_type == 1: size = 2
                elif psize_type == 2: size = 4
                elif psize_type == 3: size = 12
                elif psize_type == 4: size = 16
                elif psize_type == 5:
                    if pos >= end_pos: break
                    size = buf[pos]; pos += 1
                elif psize_type == 6:
                    if pos + 2 > end_pos: break
                    size = struct.unpack("<H", buf[pos:pos+2])[0]; pos += 2
                elif psize_type == 7:
                    if pos + 4 > end_pos: break
                    size = struct.unpack("<I", buf[pos:pos+4])[0]; pos += 4
                else:
                    size = 1

                if is_array:
                    if pos >= end_pos: break
                    b = buf[pos]
                    pos += 1
                    if b & 0x80:
                        if pos >= end_pos: break
                        pos += 1

                val_data = buf[pos : pos + size]
                pos += size

                if pname.lower() == "staticmesh" and len(val_data) > 0:
                    obj_ref_idx, _ = read_compact_index(val_data, 0)
                    ref_str = self._resolve_object_ref(obj_ref_idx)
                    if ref_str:
                        return ref_str
        except Exception:
            pass

        # Fallback scanner for actors with state frames (UE2.5 / Samurai / Ver133)
        raw_slice = buf[exp.serial_offset : exp.serial_offset + exp.serial_size]
        mesh_names_idx = {i for i, n in enumerate(self.pkg.names) if n.lower() == "staticmesh"}
        for p in range(len(raw_slice) - 4):
            try:
                name_idx, p2 = read_compact_index(raw_slice, p)
                if name_idx in mesh_names_idx and p2 < len(raw_slice):
                    info = raw_slice[p2]
                    if (info & 0x0F) == 5:  # Object property
                        obj_idx, _ = read_compact_index(raw_slice, p2 + 1)
                        ref_str = self._resolve_object_ref(obj_idx)
                        if ref_str:
                            return ref_str
            except Exception:
                pass

        return None

    def _extract_terrain_info(self, exp) -> TerrainData:
        """Extracts TerrainMap (heightmap) and layer configuration from TerrainInfo."""
        td = TerrainData(
            actor_name=exp.object_name,
            heightmap_texture="Unknown",
        )

        buf = self.pkg.raw_data
        pos = exp.serial_offset
        end_pos = pos + exp.serial_size

        while pos < end_pos:
            name_idx, pos = read_compact_index(buf, pos)
            pname = self.pkg.names[name_idx] if 0 <= name_idx < len(self.pkg.names) else ""
            if pname == "None":
                break

            info = buf[pos]
            pos += 1
            ptype = info & 0x0F
            psize_type = (info >> 4) & 0x07
            is_array = (info >> 7) & 0x01

            if ptype == 3:  # Boolean property has 0 data bytes
                size = 0
            elif psize_type == 0: size = 1
            elif psize_type == 1: size = 2
            elif psize_type == 2: size = 4
            elif psize_type == 3: size = 12
            elif psize_type == 4: size = 16
            elif psize_type == 5:
                size = buf[pos]; pos += 1
            elif psize_type == 6:
                size = struct.unpack("<H", buf[pos:pos+2])[0]; pos += 2
            elif psize_type == 7:
                size = struct.unpack("<I", buf[pos:pos+4])[0]; pos += 4
            else:
                size = 1

            if is_array:
                b = buf[pos]
                pos += 1
                if b & 0x80:
                    pos += 1

            val_data = buf[pos : pos + size]
            pos += size

            if pname.lower() == "terrainmap" and len(val_data) > 0:
                obj_ref_idx, _ = read_compact_index(val_data, 0)
                td.heightmap_texture = self._resolve_object_ref(obj_ref_idx)
            elif pname.lower() == "terrainscale" and len(val_data) >= 12:
                sx, sy, sz = struct.unpack("<fff", val_data[:12])
                td.terrain_scale = (sx, sy, sz)

        return td
