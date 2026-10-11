#!/usr/bin/env python3
"""Render a labelled, magnified contact sheet of any generator's ART table.

Why this exists: reviewing pixel art by reading ASCII rows is unreliable — the
only trustworthy check is to look at the actual rendered pixels. This tool
scales every sprite up and stamps its name underneath with a built-in 3x5
bitmap font, so a defect ("tri_left is a hollow chevron, not a solid triangle")
is visible at a glance instead of being inferred.

Usage:
    python tools/inspect_art.py make_vqeaf_studio_icons 8
    python tools/inspect_art.py make_vqeaf_icons 8 --only wifi,bluetooth

Output: <exports>/<module>/_inspect_<scale>x.png
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vpx_editor.vpe import rgb_to_565  # noqa: E402

# 3x5 uppercase + digits + a few symbols. '#' = ink, '.' = clear.
FONT: Dict[str, List[str]] = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": ["..#", "..#", "..#", "..#", "..#"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    "A": ["###", "#.#", "###", "#.#", "#.#"],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"],
    "N": ["#.#", "###", "###", "###", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"],
    "P": ["###", "#.#", "###", "#..", "#.."],
    "Q": ["###", "#.#", "#.#", "###", "..#"],
    "R": ["###", "#.#", "###", "##.", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", "###", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"],
    "_": ["...", "...", "...", "...", "###"],
    "-": ["...", "...", "###", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."],
}


class Canvas:
    """Tiny RGB565 canvas; only used for inspection output, never shipped."""

    def __init__(self, w: int, h: int, bg: int) -> None:
        self.w = w
        self.h = h
        self.px = [bg] * (w * h)

    def set(self, x: int, y: int, c: int) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def text(self, x: int, y: int, s: str, c: int, scale: int = 1) -> None:
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT["."])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == "#":
                        for sy in range(scale):
                            for sx in range(scale):
                                self.set(cx + gx * scale + sx, y + gy * scale + sy, c)
            cx += 4 * scale


def build(art: Dict[str, Sequence[str]], size: int, scale: int, cols: int,
          bg: int, ink: int, label_scale: int) -> Canvas:
    names = list(art.keys())
    # Label must fit the cell: 4px per glyph at label_scale vs (size*scale+8) cell.
    max_chars = max(1, (size * scale + 8) // (4 * label_scale))
    label_h = 5 * label_scale
    cell_w = size * scale + 8
    cell_h = size * scale + label_h + 10
    rows = (len(names) + cols - 1) // cols
    cv = Canvas(cols * cell_w, rows * cell_h, bg)
    for i, name in enumerate(names):
        gx = (i % cols) * cell_w + 4
        gy = (i // cols) * cell_h + 4
        rows_art = art[name]
        for y in range(min(size, len(rows_art))):
            row = rows_art[y]
            for x in range(min(size, len(row))):
                if row[x] == ".":
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        cv.set(gx + x * scale + sx, gy + y * scale + sy, ink)
        cv.text(gx, gy + size * scale + 4, name[:max_chars], ink, scale=label_scale)
    return cv


def encode_png_rgba(path: Path, w: int, h: int, pixels: Sequence[int]) -> None:
    """Stdlib PNG writer. save_png() lives in vpe.py but needs Qt/QImage."""
    import struct
    import zlib

    def c565(v: int):
        return ((v >> 11) & 0x1F) * 255 // 31, ((v >> 5) & 0x3F) * 255 // 63, (v & 0x1F) * 255 // 31

    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(c565(pixels[y * w + x]))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("usage: inspect_art.py <module> [scale] [--only a,b,c]")
        return 2
    module_name = argv[1]
    scale = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 8

    mod = importlib.import_module(module_name)
    art: Dict[str, Sequence[str]] = dict(mod.ART)

    if "--only" in argv:
        want = set(argv[argv.index("--only") + 1].split(","))
        art = {k: v for k, v in art.items() if k in want}

    size = getattr(mod, "SIZE", len(next(iter(art.values()))))
    bg = rgb_to_565(18, 20, 28)
    ink = rgb_to_565(236, 240, 250)
    cols = 8 if len(art) > 12 else min(len(art), 6)
    label_scale = max(1, min(2, scale // 4))

    cv = build(art, size, scale, cols, bg, ink, label_scale)
    sub = argv[argv.index("--out") + 1] if "--out" in argv else module_name
    out_dir = Path.home() / "Documents" / "VPE Pixel" / "exports" / sub
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"_inspect_{scale}x.png"
    encode_png_rgba(out, cv.w, cv.h, cv.px)
    print(f"{out}  ({cv.w}x{cv.h}, {len(art)} icons @ {scale}x, labels @ {label_scale}x)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
