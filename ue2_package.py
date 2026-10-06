#!/usr/bin/env python3
"""
Unreal Engine 2 Package Parser for Lineage 2
Parses FPackageFileSummary, FNameTable, FObjectImport, and FObjectExport tables.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

from l2_crypt import decrypt_package_file, decrypt_package_data, UNREAL_MAGIC


def read_compact_index(buf: bytes, pos: int) -> Tuple[int, int]:
    """
    Decodes an Unreal Engine compact integer index.
    Returns: (value, new_position)
    """
    b = buf[pos]
    pos += 1
    sign = b & 0x80
    shift = 6
    result = b & 0x3F
    if b & 0x40:
        while True:
            b = buf[pos]
            pos += 1
            result |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80) or shift >= 32:
                break
    if sign:
        result = -result
    return result, pos


@dataclass
class PackageSummary:
    tag: int
    file_version: int
    licensee_mode: int
    package_flags: int
    name_count: int
    name_offset: int
    export_count: int
    export_offset: int
    import_count: int
    import_offset: int
    guid: bytes = b""
    generations: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class ImportEntry:
    index: int  # 0-indexed in table
    class_package: str
    class_name: str
    package_index: int  # Outer index (< 0 is import, > 0 is export, 0 is root)
    object_name: str
    full_path: str = ""
    top_package: str = ""


@dataclass
class ExportEntry:
    index: int
    class_index: int
    super_index: int
    package_index: int
    object_name: str
    object_flags: int
    serial_size: int
    serial_offset: int
    class_name: str = ""
    full_path: str = ""


class UE2Package:
    """Represents a parsed Unreal Engine 2 package."""

    def __init__(self, filename: str, raw_data: bytes, l2_version: int = 0):
        self.filename = filename
        self.raw_data = raw_data
        self.l2_version = l2_version

        self.summary: Optional[PackageSummary] = None
        self.names: List[str] = []
        self.imports: List[ImportEntry] = []
        self.exports: List[ExportEntry] = []

        self._parse()

    @classmethod
    def load_from_file(cls, file_path: str | Path) -> UE2Package:
        p = Path(file_path)
        decrypted_bytes, version = decrypt_package_file(p)
        return cls(p.name, decrypted_bytes, version)

    def _parse(self):
        buf = self.raw_data
        if len(buf) < 36:
            raise ValueError(f"Package {self.filename} is too small to be valid.")

        tag, ver, lic, flags, n_count, n_off, e_count, e_off, i_count, i_off = struct.unpack(
            "<IHHIIIIIII", buf[:36]
        )
        if tag != UNREAL_MAGIC:
            raise ValueError(f"Invalid UE2 magic in {self.filename}: 0x{tag:08X}")

        self.summary = PackageSummary(
            tag=tag,
            file_version=ver,
            licensee_mode=lic,
            package_flags=flags,
            name_count=n_count,
            name_offset=n_off,
            export_count=e_count,
            export_offset=e_off,
            import_count=i_count,
            import_offset=i_off,
        )

        self._parse_names()
        self._parse_imports()
        self._parse_exports()
        self._resolve_paths()

    def _parse_names(self):
        buf = self.raw_data
        pos = self.summary.name_offset
        self.names = []

        for _ in range(self.summary.name_count):
            length, pos = read_compact_index(buf, pos)
            if length > 0:
                s = buf[pos : pos + length].rstrip(b"\x00").decode("latin1", errors="replace")
                pos += length
            elif length < 0:
                ulen = -length * 2
                s = buf[pos : pos + ulen].rstrip(b"\x00\x00").decode("utf-16le", errors="replace")
                pos += ulen
            else:
                s = ""
            # Skip 4-byte FName flags
            pos += 4
            self.names.append(s)

    def _parse_imports(self):
        buf = self.raw_data
        pos = self.summary.import_offset
        self.imports = []

        for i in range(self.summary.import_count):
            class_pkg_idx, pos = read_compact_index(buf, pos)
            class_name_idx, pos = read_compact_index(buf, pos)
            pkg_idx = struct.unpack("<i", buf[pos : pos + 4])[0]
            pos += 4
            obj_name_idx, pos = read_compact_index(buf, pos)

            cp = self.names[class_pkg_idx] if 0 <= class_pkg_idx < len(self.names) else "Unknown"
            cn = self.names[class_name_idx] if 0 <= class_name_idx < len(self.names) else "Unknown"
            on = self.names[obj_name_idx] if 0 <= obj_name_idx < len(self.names) else "Unknown"

            entry = ImportEntry(
                index=i,
                class_package=cp,
                class_name=cn,
                package_index=pkg_idx,
                object_name=on,
            )
            self.imports.append(entry)

    def _parse_exports(self):
        buf = self.raw_data
        pos = self.summary.export_offset
        self.exports = []

        for i in range(self.summary.export_count):
            class_idx, pos = read_compact_index(buf, pos)
            super_idx, pos = read_compact_index(buf, pos)
            pkg_idx = struct.unpack("<i", buf[pos : pos + 4])[0]
            pos += 4
            obj_name_idx, pos = read_compact_index(buf, pos)
            obj_flags = struct.unpack("<I", buf[pos : pos + 4])[0]
            pos += 4
            serial_size, pos = read_compact_index(buf, pos)
            serial_offset = 0
            if serial_size > 0:
                serial_offset, pos = read_compact_index(buf, pos)

            on = self.names[obj_name_idx] if 0 <= obj_name_idx < len(self.names) else "Unknown"

            entry = ExportEntry(
                index=i,
                class_index=class_idx,
                super_index=super_idx,
                package_index=pkg_idx,
                object_name=on,
                object_flags=obj_flags,
                serial_size=serial_size,
                serial_offset=serial_offset,
            )
            self.exports.append(entry)

    def _resolve_paths(self):
        """Resolves the full object path and top-level package for all imports."""
        for imp in self.imports:
            chain = [imp.object_name]
            curr_pkg = imp.package_index

            visited: Set[int] = set()
            while curr_pkg < 0:
                if curr_pkg in visited:
                    break
                visited.add(curr_pkg)

                parent_imp_idx = -curr_pkg - 1
                if 0 <= parent_imp_idx < len(self.imports):
                    parent = self.imports[parent_imp_idx]
                    chain.append(parent.object_name)
                    curr_pkg = parent.package_index
                else:
                    break

            chain.reverse()
            imp.full_path = ".".join(chain)
            imp.top_package = chain[0] if chain else imp.object_name

    def get_imported_packages(self) -> Set[str]:
        """Returns the set of all top-level package names imported."""
        return {imp.top_package for imp in self.imports if imp.top_package}

    def get_imports_by_class(self, class_name: str) -> List[ImportEntry]:
        """Returns all import entries matching a specific class (e.g. 'StaticMesh', 'Texture')."""
        return [imp for imp in self.imports if imp.class_name.lower() == class_name.lower()]
