#!/usr/bin/env python3
"""Build the bundled numeral font from the pinned upstream Noto Sans JP OTF.

Development utility only: needs libharfbuzz and libharfbuzz-subset. Runtime
loads the resulting OTF directly through Qt and needs no subsetting tools.
"""
import ctypes as c
import hashlib
from pathlib import Path
import struct
import sys

SOURCE_SHA256 = "dff723ba59d57d136764a04b9b2d03205544f7cd785a711442d6d2d085ac5073"
CHARS = " 一二三四五六七八九十0123456789"


def checksum(data):
    data += b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(data) // 4}I", data)) & 0xFFFFFFFF


def rename_font(data):
    """Rename public family/PS names while retaining copyright and OFL records."""
    count = struct.unpack_from(">H", data, 4)[0]
    tables = {}
    for index in range(count):
        tag, _, offset, size = struct.unpack_from(">4sIII", data, 12 + index * 16)
        tables[tag] = data[offset:offset + size]
    names = tables[b"name"]
    _, records, start = struct.unpack_from(">HHH", names)
    replacements = {1: "DanShell Workspace Kanji", 2: "Regular",
                    3: "DanShellWorkspaceKanji-Regular-1.0",
                    4: "DanShell Workspace Kanji Regular",
                    6: "DanShellWorkspaceKanji-Regular",
                    16: "DanShell Workspace Kanji", 17: "Regular"}
    directory = bytearray()
    strings = bytearray()
    for index in range(records):
        platform, encoding, language, name_id, length, offset = struct.unpack_from(">6H", names, 6 + index * 12)
        value = names[start + offset:start + offset + length]
        if name_id in replacements:
            codec = "utf-16-be" if platform in (0, 3) else "mac_roman"
            value = replacements[name_id].encode(codec)
        directory.extend(struct.pack(">6H", platform, encoding, language,
                                     name_id, len(value), len(strings)))
        strings.extend(value)
    tables[b"name"] = struct.pack(">3H", 0, records, 6 + len(directory)) + directory + strings
    head = bytearray(tables[b"head"])
    head[8:12] = b"\0" * 4
    tables[b"head"] = bytes(head)
    out = bytearray(data[:12] + b"\0" * (16 * count))
    head_offset = None
    for index, (tag, table) in enumerate(sorted(tables.items())):
        offset = len(out)
        struct.pack_into(">4sIII", out, 12 + index * 16, tag, checksum(table), offset, len(table))
        if tag == b"head":
            head_offset = offset
        out.extend(table)
        out.extend(b"\0" * (-len(table) % 4))
    struct.pack_into(">I", out, head_offset + 8, (0xB1B0AFBA - checksum(bytes(out))) & 0xFFFFFFFF)
    return bytes(out)


def build(source, output):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source font does not match the pinned upstream revision")
    hb = c.CDLL("libharfbuzz.so.0")
    subset = c.CDLL("libharfbuzz-subset.so.0")
    def bind(lib, name, result, args):
        function = getattr(lib, name)
        function.restype = result
        function.argtypes = args
        return function
    ptr, uint = c.c_void_p, c.c_uint
    blob = bind(hb, "hb_blob_create_from_file_or_fail", ptr, [c.c_char_p])(bytes(source))
    face = bind(hb, "hb_face_create", ptr, [ptr, uint])(blob, 0)
    config = bind(subset, "hb_subset_input_create_or_fail", ptr, [])()
    codepoints = bind(subset, "hb_subset_input_unicode_set", ptr, [ptr])(config)
    bind(hb, "hb_set_clear", None, [ptr])(codepoints)
    add = bind(hb, "hb_set_add", None, [ptr, uint])
    names = bind(subset, "hb_subset_input_set", ptr, [ptr, uint])(config, 4)
    for name_id in (13, 14, 16, 17):
        add(names, name_id)
    for char in CHARS:
        add(codepoints, ord(char))
    result = bind(subset, "hb_subset_or_fail", ptr, [ptr, ptr])(face, config)
    if not result:
        raise RuntimeError("HarfBuzz could not subset the font")
    result_blob = bind(hb, "hb_face_reference_blob", ptr, [ptr])(result)
    size = uint()
    address = bind(hb, "hb_blob_get_data", ptr, [ptr, c.POINTER(uint)])(result_blob, c.byref(size))
    output.write_bytes(rename_font(c.string_at(address, size.value)))
    for item in (result_blob, blob):
        bind(hb, "hb_blob_destroy", None, [ptr])(item)
    for item in (result, face):
        bind(hb, "hb_face_destroy", None, [ptr])(item)
    bind(subset, "hb_subset_input_destroy", None, [ptr])(config)


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(__file__).with_name("workspace-kanji.otf"))
