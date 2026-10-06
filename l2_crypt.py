#!/usr/bin/env python3
"""
Lineage 2 Package Decryption & Encryption Module
Supports Lineage2Ver111, Lineage2Ver120, Lineage2Ver121, Lineage2Ver211, Lineage2Ver212, Lineage2Ver413, and raw UE2 packages.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Tuple, Optional

# Constants
HEADER_LEN = 28
LINEAGE_PREFIX = "Lineage2Ver"
UNREAL_MAGIC = 0x9E2A83C1  # Little endian: c1 83 2a 9e
ALIAS_KEY = "Range check error while converting variant of type (%s) into type (%s)".encode("latin1")

VER211_KEY = b"31==-%&@!^+][;'.]94-\x00"
VER212_KEY = b"[;'.]94-&@%!^+]-31==\x00"

VER413_MODULUS = int(
    "97df398472ddf737ef0a0cd17e8d172f0fef1661a38a8ae1d6e829bc1c6e4c3c"
    "fc19292dda9ef90175e46e7394a18850b6417d03be6eea274d3ed1dde5b5d7bd"
    "e72cc0a0b71d03608655633881793a02c9a67d9ef2b45eb7c08d4be329083ce4"
    "50e68f7867b6749314d40511d09bc5744551baa86a89dc38123dc1668fd72d83",
    16,
)
VER413_PUBLIC_EXPONENT = 0x35

VER413_ENCDEC_MODULUS = int(
    "75B4D6DE5C016544068A1ACF125869F43D2E09FC55B8B1E289556DAF9B875763"
    "5593446288B3653DA1CE91C87BB1A5C18F16323495C55D7D72C0890A83F69BFD"
    "1FD9434EB1C02F3E4679EDFA43309319070129C267C85604D87BB65BAE205DE370"
    "7AF1D2108881ABB567C3B3D069AE67C3A4C6A3AA93D26413D4C66094AE2039",
    16,
)
VER413_ENCDEC_PUBLIC_EXPONENT = 0x1D

ALIASES = {
    811: 111,
    820: 120,
    821: 121,
    911: 211,
    912: 212,
}


def read_header_version(data: bytes) -> Optional[int]:
    """Reads Lineage2Ver header version if present."""
    if len(data) < HEADER_LEN:
        return None
    try:
        text = data[:HEADER_LEN].decode("utf-16le")
    except UnicodeDecodeError:
        return None
    if not text.startswith(LINEAGE_PREFIX):
        return None
    suffix = text[len(LINEAGE_PREFIX):]
    return int(suffix) if suffix.isdigit() and len(suffix) == 3 else None


def xor_fixed(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def xor_pos_key(pos: int) -> int:
    low = pos & 0xF
    high = (pos >> 4) & 0xF
    upper = (pos >> 8) & 0xF
    top = (pos >> 12) & 0xF
    return ((high ^ top) << 4) | (low ^ upper)


def xor_pos(data: bytes, start: int = 230) -> bytes:
    return bytes(b ^ xor_pos_key(start + idx) for idx, b in enumerate(data))


def filename_key(name: str) -> int:
    return sum(ord(c) for c in name.lower()) & 0xFF


def alias_xor(data: bytes) -> bytes:
    offset = HEADER_LEN % len(ALIAS_KEY)
    out = bytearray(len(data))
    for idx, b in enumerate(data):
        out[idx] = b ^ ALIAS_KEY[(offset + idx) % len(ALIAS_KEY)]
    return bytes(out)


def swap_block_words(data: bytes) -> bytes:
    swapped = bytearray(len(data))
    for offset in range(0, len(data), 8):
        swapped[offset : offset + 4] = data[offset : offset + 4][::-1]
        swapped[offset + 4 : offset + 8] = data[offset + 4 : offset + 8][::-1]
    return bytes(swapped)


def blowfish_decrypt(data: bytes, key: bytes) -> bytes:
    try:
        from cryptography.hazmat.decrepit.ciphers import algorithms as decrepit_algorithms
        from cryptography.hazmat.primitives.ciphers import Cipher, modes
    except ImportError:
        raise RuntimeError("Cryptography library required for Lineage2Ver211/212 decrypt.")

    cipher = Cipher(decrepit_algorithms.Blowfish(key), modes.ECB())
    ctx = cipher.decryptor()
    return swap_block_words(ctx.update(swap_block_words(data)) + ctx.finalize())


def rsa413_decrypt(data: bytes) -> bytes:
    if len(data) < 20 or (len(data) - 20) % 128:
        raise ValueError("Lineage2Ver413 payload has an invalid RSA block size")

    candidates = (
        (VER413_MODULUS, VER413_PUBLIC_EXPONENT),
        (VER413_ENCDEC_MODULUS, VER413_ENCDEC_PUBLIC_EXPONENT),
    )
    last_error: Optional[ValueError] = None
    compressed = bytearray()
    for modulus, exponent in candidates:
        try:
            compressed.clear()
            for offset in range(0, len(data) - 20, 128):
                encrypted = int.from_bytes(data[offset : offset + 128], "big")
                decrypted = pow(encrypted, exponent, modulus).to_bytes(128, "big")
                size = int.from_bytes(decrypted[:4], "big", signed=True)
                padding = ((-size) & 1) + ((-size) & 2)
                start = 128 - size - padding
                if size < 0 or size > 124 or start < 4:
                    raise ValueError(f"Lineage2Ver413 RSA block has invalid size {size}")
                compressed.extend(decrypted[start : start + size])
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise last_error or ValueError("Lineage2Ver413 RSA key mismatch")

    if len(compressed) < 4:
        raise ValueError("Lineage2Ver413 compressed payload is truncated")
    expected_size = int.from_bytes(compressed[:4], "little")
    result = zlib.decompress(compressed[4:])
    if len(result) != expected_size:
        raise ValueError(f"Lineage2Ver413 size mismatch: {len(result)} != {expected_size}")
    return result


def decrypt_package_data(data: bytes, filename: str) -> Tuple[bytes, int]:
    """
    Decrypts Lineage 2 package bytes.
    Returns: (decrypted_bytes, version) where version is 0 for unencrypted/raw packages.
    """
    version = read_header_version(data)
    if version is None:
        # Check if already a raw Unreal package (Tag: 0x9E2A83C1)
        if len(data) >= 4 and struct.unpack("<I", data[:4])[0] == UNREAL_MAGIC:
            return data, 0
        raise ValueError("Unrecognized file format (not a valid Lineage 2 or Unreal Engine package).")

    payload = data[HEADER_LEN:]
    normalized = ALIASES.get(version, version)

    if normalized != version:
        payload = alias_xor(payload)

    if normalized == 111:
        dec = xor_fixed(payload, 0xAC)
    elif normalized == 120:
        dec = xor_pos(payload)
    elif normalized == 121:
        dec = xor_fixed(payload, filename_key(filename))
    elif normalized in (211, 212):
        key = VER211_KEY if normalized == 211 else VER212_KEY
        dec = blowfish_decrypt(payload, key)
    elif normalized == 413:
        dec = rsa413_decrypt(payload)
    else:
        raise ValueError(f"Unsupported Lineage2Ver header: Lineage2Ver{version:03d}")

    # Verify decrypted magic
    if len(dec) >= 4:
        magic = struct.unpack("<I", dec[:4])[0]
        if magic != UNREAL_MAGIC:
            raise ValueError(f"Decryption failed: expected magic 0x9E2A83C1, got 0x{magic:08X}")

    return dec, version


def decrypt_package_file(file_path: Path | str) -> Tuple[bytes, int]:
    """Loads and decrypts a package from file path."""
    p = Path(file_path)
    with open(p, "rb") as f:
        data = f.read()
    return decrypt_package_data(data, p.name)
