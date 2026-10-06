#!/usr/bin/env python3
"""
Native UTX Texture Extractor for Lineage 2 / Unreal Engine 2
Extracts embedded DXT1, DXT3, DXT5, RGBA8, and G16 textures directly from .utx packages to DDS and PNG.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Callable

from PIL import Image

from ue2_package import UE2Package, read_compact_index
from l2_crypt import decrypt_package_file


# UE2 ETextureFormat enum
TEXF_P8 = 0
TEXF_RGBA7 = 1
TEXF_RGB8 = 2
TEXF_DXT1 = 3
TEXF_RGB8_2 = 4
TEXF_DXT3 = 5
TEXF_DXT5 = 6
TEXF_G16 = 8


@dataclass
class ExtractedTexture:
    name: str
    package_name: str
    width: int
    height: int
    format_id: int
    format_name: str
    mip_count: int
    raw_data: bytes
    dds_data: bytes = b""


def create_dds_header(width: int, height: int, dxt_fourcc: bytes, mip_count: int = 1) -> bytes:
    """Builds a standard 128-byte DirectX DDS file header."""
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<I", header, 4, 124)  # dwSize
    struct.pack_into("<I", header, 8, 0x00081007)  # dwFlags (CAPS | HEIGHT | WIDTH | PIXELFORMAT)
    struct.pack_into("<I", header, 12, height)
    struct.pack_into("<I", header, 16, width)
    pitch_mul = 8 if dxt_fourcc == b"DXT1" else 16
    pitch = max(1, ((width + 3) // 4)) * pitch_mul
    struct.pack_into("<I", header, 20, pitch * ((height + 3) // 4))
    struct.pack_into("<I", header, 28, mip_count)
    # ddspf
    struct.pack_into("<I", header, 76, 32)  # dwSize
    struct.pack_into("<I", header, 80, 0x04)  # DDPF_FOURCC
    header[84:88] = dxt_fourcc
    # dwCaps
    struct.pack_into("<I", header, 108, 0x00401008 if mip_count > 1 else 0x00001000)
    return bytes(header)


class UTXExtractor:
    """Extracts textures from Unreal Engine 2 .utx packages."""

    FORMAT_NAMES = {
        TEXF_P8: "P8 (Paletted)",
        TEXF_RGBA7: "RGBA7",
        TEXF_RGB8: "RGB8",
        TEXF_DXT1: "DXT1",
        TEXF_DXT3: "DXT3",
        TEXF_DXT5: "DXT5",
        TEXF_G16: "G16 (Heightmap Grayscale 16-bit)",
    }

    def __init__(self, package_path: Path | str):
        self.path = Path(package_path)
        self.package = UE2Package.load_from_file(self.path)

    def list_textures(self) -> List[Tuple[str, str, int, int]]:
        """Returns a list of (texture_name, class_name, size, offset) for all texture exports."""
        results = []
        for exp in self.package.exports:
            cls_name = self._resolve_class(exp.class_index)
            if cls_name.lower() in ("texture", "cubemap", "fractaltexture"):
                results.append((exp.object_name, cls_name, exp.serial_size, exp.serial_offset))
        return results

    def _resolve_class(self, class_idx: int) -> str:
        if class_idx < 0:
            imp_idx = -class_idx - 1
            if 0 <= imp_idx < len(self.package.imports):
                return self.package.imports[imp_idx].object_name
        elif class_idx > 0:
            exp_idx = class_idx - 1
            if 0 <= exp_idx < len(self.package.exports):
                return self.package.exports[exp_idx].object_name
        return "Unknown"

    def extract_texture(self, texture_name: str) -> Optional[ExtractedTexture]:
        target_exp = None
        for exp in self.package.exports:
            if exp.object_name.lower() == texture_name.lower():
                cls_name = self._resolve_class(exp.class_index)
                if cls_name.lower() in ("texture", "cubemap", "fractaltexture"):
                    target_exp = exp
                    break

        if not target_exp or target_exp.serial_size <= 0:
            return None

        buf = self.package.raw_data
        pos = target_exp.serial_offset
        end_pos = pos + target_exp.serial_size

        # 1. Parse Properties to get Format, USize, VSize
        fmt_id = TEXF_DXT1
        u_size = 0
        v_size = 0

        while pos < end_pos:
            name_idx, pos = read_compact_index(buf, pos)
            pname = self.package.names[name_idx] if 0 <= name_idx < len(self.package.names) else ""
            if pname == "None":
                break

            info = buf[pos]
            pos += 1
            ptype = info & 0x0F
            psize_type = (info >> 4) & 0x07
            is_array = (info >> 7) & 0x01

            if psize_type == 0: size = 1
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

            if pname == "Format" and len(val_data) >= 1:
                fmt_id = val_data[0]
            elif pname == "USize" and len(val_data) >= 4:
                u_size = struct.unpack("<I", val_data[:4])[0]
            elif pname == "VSize" and len(val_data) >= 4:
                v_size = struct.unpack("<I", val_data[:4])[0]

        # 2. Skip remaining object header bytes to reach Mipmaps array
        # In UE2, after properties end, there is often 4 bytes (or lazy array header)
        if pos + 4 <= end_pos:
            # Check for array count
            arr_count = 0
            # Scan ahead a few bytes for mip array count (usually 1..16)
            scan_pos = pos
            while scan_pos < pos + 16 and scan_pos < end_pos:
                test_count, next_pos = read_compact_index(buf, scan_pos)
                if 1 <= test_count <= 16:
                    arr_count = test_count
                    pos = next_pos
                    break
                scan_pos += 1

            if arr_count > 0 and pos + 4 <= end_pos:
                # Skip 4 bytes DataOffset
                pos += 4
                data_size, pos = read_compact_index(buf, pos)
                if data_size > 0 and pos + data_size <= len(buf):
                    raw_data = buf[pos : pos + data_size]
                    pos += data_size
                    # Read width/height if not found in properties
                    if pos + 8 <= len(buf):
                        mw, mh = struct.unpack("<II", buf[pos:pos+8])
                        if mw > 0 and mh > 0:
                            u_size, v_size = mw, mh

                    # Create DDS header if DXT
                    dds_data = b""
                    fourcc_map = {
                        TEXF_DXT1: b"DXT1",
                        TEXF_DXT3: b"DXT3",
                        TEXF_DXT5: b"DXT5",
                    }
                    if fmt_id in fourcc_map and u_size > 0 and v_size > 0:
                        hdr = create_dds_header(u_size, v_size, fourcc_map[fmt_id], mip_count=1)
                        dds_data = hdr + raw_data

                    return ExtractedTexture(
                        name=target_exp.object_name,
                        package_name=self.path.stem,
                        width=u_size,
                        height=v_size,
                        format_id=fmt_id,
                        format_name=self.FORMAT_NAMES.get(fmt_id, f"Format_{fmt_id}"),
                        mip_count=arr_count,
                        raw_data=raw_data,
                        dds_data=dds_data,
                    )

        return None

    def export_all_to_folder(
        self,
        output_dir: Path | str,
        export_png: bool = True,
        export_dds: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Path]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        tex_list = self.list_textures()
        saved_paths: List[Path] = []

        total = len(tex_list)
        for idx, (tex_name, _, _, _) in enumerate(tex_list):
            item = self.extract_texture(tex_name)
            if not item:
                continue

            # Save DDS
            if export_dds and item.dds_data:
                dds_file = out / f"{item.name}.dds"
                with open(dds_file, "wb") as f:
                    f.write(item.dds_data)
                saved_paths.append(dds_file)

            # Save PNG (via Pillow)
            if export_png and item.dds_data:
                try:
                    with Image.open(io.BytesIO(item.dds_data)) as img:
                        png_file = out / f"{item.name}.png"
                        img.save(png_file, format="PNG")
                        saved_paths.append(png_file)
                except Exception:
                    pass

            if progress_callback:
                progress_callback(idx + 1, total, tex_name)

        return saved_paths
