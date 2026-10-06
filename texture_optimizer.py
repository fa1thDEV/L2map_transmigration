#!/usr/bin/env python3
"""
Texture Optimizer & Downscaler for Lineage 2
Downscales textures to safe resolutions (1024, 512, 256) while maintaining Power-of-Two dimensions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Callable

from PIL import Image


@dataclass
class ResizeRecord:
    filename: str
    src_path: Path
    dst_path: Path
    original_size: Tuple[int, int]
    new_size: Tuple[int, int]
    original_bytes: int
    new_bytes: int
    success: bool
    error: str = ""


def get_power_of_two_dimension(dim: int, max_dim: int) -> int:
    """Clamps dimension to the nearest power of two not exceeding max_dim."""
    if dim <= 0:
        return 64
    # Find power of two <= dim
    p = 2 ** int(math.log2(dim))
    return min(p, max_dim)


def resize_image_file(
    src_path: Path | str,
    dst_path: Path | str,
    max_dimension: int = 512,
    force_power_of_two: bool = True,
) -> ResizeRecord:
    src = Path(src_path)
    dst = Path(dst_path)

    orig_bytes = src.stat().st_size if src.exists() else 0
    try:
        with Image.open(src) as img:
            w, h = img.size

            if force_power_of_two:
                new_w = get_power_of_two_dimension(w, max_dimension)
                new_h = get_power_of_two_dimension(h, max_dimension)
            else:
                scale = min(max_dimension / w, max_dimension / h, 1.0)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))

            # Only resize if dimensions actually changed
            if (new_w, new_h) != (w, h):
                # Use high-quality resampling filter (LANCZOS)
                resample_filter = getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)
                resized_img = img.resize((new_w, new_h), resample=resample_filter)
            else:
                resized_img = img

            dst.parent.mkdir(parents=True, exist_ok=True)
            # Save maintaining original format
            fmt = img.format if img.format else "PNG"
            resized_img.save(dst, format=fmt)

        new_bytes = dst.stat().st_size
        return ResizeRecord(
            filename=src.name,
            src_path=src,
            dst_path=dst,
            original_size=(w, h),
            new_size=(new_w, new_h),
            original_bytes=orig_bytes,
            new_bytes=new_bytes,
            success=True,
        )
    except Exception as e:
        return ResizeRecord(
            filename=src.name,
            src_path=src,
            dst_path=dst,
            original_size=(0, 0),
            new_size=(0, 0),
            original_bytes=orig_bytes,
            new_bytes=0,
            success=False,
            error=str(e),
        )


def batch_resize_folder(
    src_folder: Path | str,
    dst_folder: Path | str,
    max_dimension: int = 512,
    force_power_of_two: bool = True,
    extensions: Tuple[str, ...] = (".png", ".tga", ".dds", ".bmp", ".jpg", ".jpeg"),
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[ResizeRecord]:
    src_dir = Path(src_folder)
    dst_dir = Path(dst_folder)

    files = [f for f in src_dir.rglob("*") if f.is_file() and f.suffix.lower() in extensions]
    results: List[ResizeRecord] = []

    total = len(files)
    for idx, f in enumerate(files):
        rel_path = f.relative_to(src_dir)
        target_path = dst_dir / rel_path

        record = resize_image_file(
            src_path=f,
            dst_path=target_path,
            max_dimension=max_dimension,
            force_power_of_two=force_power_of_two,
        )
        results.append(record)

        if progress_callback:
            progress_callback(idx + 1, total, f.name)

    return results
