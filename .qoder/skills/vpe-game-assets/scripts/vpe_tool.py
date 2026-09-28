#!/usr/bin/env python3
"""VPE565 (.vpe) and VPEA01 (.vpea) asset pipeline for game/app development - stdlib only.

Works in any project without PySide6 / PIL installed. `.vpea` animations expand to
one atlas entry / PNG per frame, named `<stem>_00`, `<stem>_01`, ..., so a
multi-frame scene packs into the same sheet as the stills around it.

    python vpe_tool.py inspect      FILE...
    python vpe_tool.py png          FILE... [--out DIR] [--scale N] [--transparent-white]
    python vpe_tool.py atlas        FILES... --out A.png --json A.json [--dir DIR] [--scale N]
    python vpe_tool.py tileset      --dir DIR --out T.png --json T.json [--size 16] [--cols N]
    python vpe_tool.py header       FILE --lang c|py|js|json [--name IDENT] [--out FILE]
    python vpe_tool.py batch-export --dir DIR --out DIR [--scale N]

Exit code is non-zero with a one-line `ERROR:` message on failure.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

MAGIC = b"VPE565"
HEADER_SIZE = 16
MAX_DIM = 640
ANIM_MAGIC = b"VPEA01"
ANIM_HEADER_SIZE = 20


class VpeError(Exception):
    pass


# --------------------------------------------------------------- decoding
def decode_vpe(blob: bytes) -> Tuple[int, int, List[int]]:
    if len(blob) < HEADER_SIZE:
        raise VpeError("file too small to hold a VPE565 header")
    if blob[:8] != MAGIC + struct.pack("<H", 1):
        raise VpeError("bad magic - not a VPE565 file")
    w, h, payload = struct.unpack_from("<HHI", blob, 8)
    if not (1 <= w <= MAX_DIM and 1 <= h <= MAX_DIM):
        raise VpeError(f"dimensions {w}x{h} out of range")
    if payload != w * h * 2 or len(blob) != HEADER_SIZE + payload:
        raise VpeError(f"payload size mismatch (want {w * h * 2}, got {payload})")
    return w, h, list(struct.unpack_from(f"<{w * h}H", blob, HEADER_SIZE))


def decode_vpea(blob: bytes) -> Tuple[int, int, List[List[int]], int, bool]:
    """VPEA01 container -> (w, h, frames, delay_ms, loop)."""
    if len(blob) < ANIM_HEADER_SIZE or blob[:8] != ANIM_MAGIC + struct.pack("<H", 1):
        raise VpeError("bad magic - not a VPEA01 file")
    w, h, count, delay, loop = struct.unpack_from("<HHHHB", blob, 8)
    body = 16 + w * h * 2
    if not (1 <= w <= MAX_DIM and 1 <= h <= MAX_DIM):
        raise VpeError(f"dimensions {w}x{h} out of range")
    if count < 1 or len(blob) != ANIM_HEADER_SIZE + count * body:
        raise VpeError(f"frame count / size mismatch ({count} frames)")
    frames = [decode_vpe(blob[ANIM_HEADER_SIZE + i * body:][:body])[2]
              for i in range(count)]
    return w, h, frames, delay, bool(loop)


def frames_of(path: Path) -> List[Tuple[str, int, int, List[int], Optional[dict]]]:
    """Every image a file contributes: (entry name, w, h, pixels, animation meta).

    Stills keep their file name (`.vpe` included) because existing engine lookups
    key on it; only expanded animation frames get a `<stem>_NN` name.
    """
    p = Path(path)
    blob = p.read_bytes()
    if blob[:6] == ANIM_MAGIC:
        w, h, frames, delay, loop = decode_vpea(blob)
        if len(frames) == 1:
            return [(p.name, w, h, frames[0], None)]
        return [(f"{p.stem}_{i:02d}", w, h, f,
                 {"source": p.name, "frame": i, "frameCount": len(frames),
                  "delayMs": delay, "loop": loop})
                for i, f in enumerate(frames)]
    w, h, px = decode_vpe(blob)
    return [(p.name, w, h, px, None)]


def c565_to_rgb(v: int) -> Tuple[int, int, int]:
    return ((v >> 11) & 31) * 8, ((v >> 5) & 63) * 4, (v & 31) * 8


def to_rgba(w: int, h: int, px: Sequence[int], transparent_white: bool = False) -> bytes:
    """RGB565 -> 8-bit RGBA rows. VPE has no alpha, so white is opaque by default."""
    out = bytearray(w * h * 4)
    for i, v in enumerate(px):
        r, g, b = c565_to_rgb(v)
        o = i * 4
        out[o] = r
        out[o + 1] = g
        out[o + 2] = b
        out[o + 3] = 0 if (transparent_white and v == 0xFFFF) else 255
    return bytes(out)


def scale_rgba(rgba: bytes, w: int, h: int, factor: int) -> Tuple[bytes, int, int]:
    if factor <= 1:
        return rgba, w, h
    nw, nh = w * factor, h * factor
    out = bytearray(nw * nh * 4)
    for y in range(nh):
        srow = (y // factor) * w * 4
        drow = y * nw * 4
        for x in range(nw):
            s = srow + (x // factor) * 4
            d = drow + x * 4
            out[d:d + 4] = rgba[s:s + 4]
    return bytes(out), nw, nh


# ------------------------------------------------------------------- PNG
def write_png(path: Path, w: int, h: int, rgba: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


# ----------------------------------------------------------------- atlas
def pack_shelf(items: List[Tuple[str, int, int]], pad: int = 1
               ) -> Tuple[List[Tuple[str, int, int, int, int]], int, int]:
    """Shelf-pack rects by descending height; returns placements + atlas size."""
    order = sorted(items, key=lambda t: (-t[2], -t[1]))
    total_area = sum(w * h for _, w, h in order)
    widest = max(w + 2 * pad for _, w, _ in order)
    width = max(widest, int(math.ceil(math.sqrt(total_area))))
    placements: List[Tuple[str, int, int, int, int]] = []
    x = y = row_h = 0
    for name, w, h in order:
        if x > 0 and x + w + pad > width:
            x = 0
            y += row_h + pad
            row_h = 0
        placements.append((name, x, y, w, h))
        x += w + pad
        row_h = max(row_h, h)
    return placements, max(width, x + pad), y + row_h + pad


def build_atlas(entries: List[Tuple[str, int, int, bytes, Optional[dict]]],
                pad: int = 1) -> Tuple[bytes, int, int, List[dict]]:
    """entries: (name, w, h, rgba, extra meta). Returns atlas rgba, width, height, records."""
    items = [(name, w, h) for name, w, h, _, _ in entries]
    placements, aw, ah = pack_shelf(items, pad)
    canvas = bytearray(aw * ah * 4)  # fully transparent gutter
    by_name = {e[0]: e for e in entries}
    frames = []
    for name, x, y, w, h in placements:
        entry = by_name[name]
        rgba = entry[3]
        for row in range(h):
            d = ((y + row) * aw + x) * 4
            s = row * w * 4
            canvas[d:d + w * 4] = rgba[s:s + w * 4]
        rec = {"filename": name, "textureRect": {"x": x, "y": y, "w": w, "h": h}}
        if entry[4]:
            rec.update(entry[4])
        frames.append(rec)
    return bytes(canvas), aw, ah, frames


# ----------------------------------------------------------------- utils
def collect_dir(folder: Path, recursive: bool = True) -> List[Path]:
    star = "**" if recursive else ""
    return sorted(list(folder.glob(f"{star}/*.vpe")) + list(folder.glob(f"{star}/*.vpea")),
                  key=lambda p: (p.name.lower(), p.suffix))


# ------------------------------------------------------------- commands
def cmd_inspect(a: argparse.Namespace) -> int:
    for f in a.files:
        p = Path(f)
        try:
            frames = frames_of(p)
        except (OSError, VpeError) as e:
            print(f"ERROR  {p}: {e}")
            continue
        w, h = frames[0][1], frames[0][2]
        anim = frames[0][4]
        tag = (f"  {anim['frameCount']}-frame animation @{anim['delayMs']} ms"
               f" loop={str(anim['loop']).lower()}" if anim else "")
        print(f"{p.name}  {w}x{h}  images={len(frames)}"
              f"  {p.stat().st_size} bytes{tag}")
    return 0


def cmd_png(a: argparse.Namespace) -> int:
    for f in a.files:
        p = Path(f)
        try:
            frames = frames_of(p)
        except (OSError, VpeError) as e:
            print(f"ERROR  {p}: {e}")
            continue
        for name, w, h, px, meta in frames:
            rgba = to_rgba(w, h, px, a.transparent_white)
            rgba, w, h = scale_rgba(rgba, w, h, a.scale)
            base = p.stem if meta is None else name
            if a.out:
                dest = Path(a.out)
                dest = (dest / (base + ".png") if (dest.is_dir() or len(frames) > 1)
                        else dest)
            else:
                dest = p.with_name(base + ".png")
            write_png(dest, w, h, rgba)
            print(f"OK  {dest}  {w}x{h}")
    return 0


def cmd_atlas(a: argparse.Namespace) -> int:
    files = list(a.files)
    if a.dir:
        files += collect_dir(Path(a.dir))
    if not files:
        print("ERROR  no .vpe/.vpea files given (pass files or --dir)")
        return 2
    entries, skipped, animated = [], 0, 0
    for f in files:
        p = Path(f)
        try:
            frames = frames_of(p)
        except (OSError, VpeError) as e:
            print(f"ERROR  {p}: {e}")
            skipped += 1
            continue
        animated += len(frames) - 1
        for name, w, h, px, meta in frames:
            rgba = to_rgba(w, h, px, a.transparent_white)
            rgba, w, h = scale_rgba(rgba, w, h, a.scale)
            entries.append((name, w, h, rgba, meta))
    if not entries:
        print("ERROR  nothing to pack")
        return 2
    rgba, aw, ah, frames = build_atlas(entries)
    atlas = Path(a.out)
    write_png(atlas, aw, ah, rgba)
    meta = {
        "image": atlas.name,
        "width": aw,
        "height": ah,
        "scale": a.scale,
        "transparentWhite": a.transparent_white,
        "format": "VPE565/RGB565 -> RGBA8",
        "frames": frames,
    }
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"OK  {atlas}  {aw}x{ah}  frames={len(frames)}"
          + (f"  animFrames={animated}" if animated else "")
          + (f"  {a.json}" if a.json else "")
          + (f"  skipped={skipped}" if skipped else ""))
    return 0


def cmd_tileset(a: argparse.Namespace) -> int:
    folder = Path(a.dir)
    files = collect_dir(folder, not a.no_recursive)
    tiles = []
    for p in files:
        try:
            frames = frames_of(p)
        except (OSError, VpeError) as e:
            print(f"ERROR  {p}: {e}")
            continue
        for name, w, h, px, _meta in frames:
            if a.size and (w != a.size or h != a.size):
                continue
            rgba = to_rgba(w, h, px, a.transparent_white)
            rgba, w, h = scale_rgba(rgba, w, h, a.scale)
            tiles.append((name, w, h, rgba, None))
    if not tiles:
        print(f"ERROR  no {a.size}x{a.size} tiles found under {folder}")
        return 2
    tw, th = tiles[0][1], tiles[0][2]
    if any(t[1] != tw or t[2] != th for t in tiles):
        print("ERROR  tileset needs uniform tile size (use --size to filter)")
        return 2
    cols = a.cols or max(1, int(math.ceil(math.sqrt(len(tiles)))))
    rows = int(math.ceil(len(tiles) / cols))
    aw, ah = cols * tw, rows * th
    canvas = bytearray(aw * ah * 4)
    for i, (name, _, _, rgba, _meta) in enumerate(tiles):
        x, y = (i % cols) * tw, (i // cols) * th
        for row in range(th):
            d = ((y + row) * aw + x) * 4
            s = row * tw * 4
            canvas[d:d + tw * 4] = rgba[s:s + tw * 4]
    out = Path(a.out)
    write_png(out, aw, ah, bytes(canvas))
    meta = {
        "image": out.name,
        "tileWidth": tw,
        "tileHeight": th,
        "columns": cols,
        "rows": rows,
        "tileCount": len(tiles),
        "spacing": 0,
        "margin": 0,
        "transparentWhite": a.transparent_white,
        "tiles": [{"index": i, "name": n} for i, (n, _, _, _, _) in enumerate(tiles)],
    }
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"OK  {out}  {aw}x{ah}  {cols}x{rows} of {tw}x{th}  tiles={len(tiles)}"
          + (f"  {a.json}" if a.json else ""))
    return 0


def cmd_header(a: argparse.Namespace) -> int:
    p = Path(a.file)
    try:
        images = frames_of(p)
    except (OSError, VpeError) as e:
        print(f"ERROR  {p}: {e}")
        return 2
    if len(images) > 1:
        print(f"ERROR  {p.name} is a {len(images)}-frame animation - "
              f"header embeds one still; use atlas/png for the frames")
        return 2
    _entry, w, h, px, _meta = images[0]
    name = (a.name or p.stem).replace("-", "_").replace(".", "_")
    if not name.isidentifier():
        name = "asset_" + "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    if a.lang == "json":
        body = json.dumps({"name": name, "width": w, "height": h,
                           "format": "rgb565_le", "pixels": px}, indent=2)
    elif a.lang == "c":
        rows = [", ".join(f"0x{v:04X}" + ("" if i == len(px) - 1 else ",")
                          for i, v in enumerate(px[s:s + 8]))
                for s in range(0, len(px), 8)]
        body = (f"/* {p.name} - VPE565 {w}x{h}, RGB565 little-endian */\n"
                f"#ifndef {name.upper()}_H\n#define {name.upper()}_H\n\n"
                f"#define {name.upper()}_W {w}\n#define {name.upper()}_H {h}\n"
                f"#define {name.upper()}_LEN {len(px)}\n\n"
                f"static const unsigned short {name}[{name.upper()}_LEN] = {{\n"
                + "\n".join("    " + r for r in rows)
                + "\n};\n\n#endif\n")
    elif a.lang == "py":
        body = (f"# {p.name} - VPE565 {w}x{h}, RGB565\n"
                f"NAME = {name!r}\nWIDTH = {w}\nHEIGHT = {h}\n"
                f"PIXELS = {px!r}\n")
    else:  # js
        body = (f"// {p.name} - VPE565 {w}x{h}, RGB565\n"
                f"export const {name} = {{\n  name: {json.dumps(name)},"
                f"\n  width: {w},\n  height: {h},\n  pixels: {json.dumps(px)},\n}};\n")
    dest = Path(a.out) if a.out else None
    if dest:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body, encoding="utf-8")
        print(f"OK  {dest}  {w}x{h}  {a.lang}")
    else:
        print(body)
    return 0


def cmd_batch_export(a: argparse.Namespace) -> int:
    src = Path(a.dir)
    out = Path(a.out)
    files = collect_dir(src)
    if not files:
        print(f"ERROR  no .vpe/.vpea files under {src}")
        return 2
    categories = ("titleset", "sprite", "texture", "tile")
    by_cat: Dict[str, List[Tuple[str, int, int, bytes, Optional[dict]]]] = {}
    images = 0
    for p in files:
        try:
            frames = frames_of(p)
        except (OSError, VpeError) as e:
            print(f"ERROR  {p}: {e}")
            continue
        rel = p.relative_to(src)
        cat = next((par.name for par in reversed(rel.parents) if par.name in categories), None)
        if cat is None:
            # Project sub-folder (e.g. a game name) or loose files at the root.
            cat = rel.parts[0] if len(rel.parts) > 1 else "misc"
        cat = "".join(c if c.isalnum() or c in "-_" else "_" for c in cat).lower()
        for name, w, h, px, meta in frames:
            rgba = to_rgba(w, h, px, a.transparent_white)
            rgba, w, h = scale_rgba(rgba, w, h, a.scale)
            by_cat.setdefault(cat, []).append((name, w, h, rgba, meta))
            images += 1
    written = []
    for cat, entries in sorted(by_cat.items()):
        rgba, aw, ah, frames = build_atlas(entries)
        png = out / f"{cat}_atlas.png"
        write_png(png, aw, ah, rgba)
        js = out / f"{cat}_atlas.json"
        js.write_text(json.dumps({"image": png.name, "width": aw, "height": ah,
                                  "frames": frames}, indent=2), encoding="utf-8")
        written.append(f"{cat}: {png.name} {aw}x{ah} frames={len(frames)}")
    print(f"OK  exported {images} images from {len(files)} files in {src}")
    for line in written:
        print("    " + line)
    return 0


# ------------------------------------------------------------------- cli
def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="vpe_tool.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("inspect", help="print size/frame count of .vpe and .vpea files")
    s.add_argument("files", nargs="+")
    s.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("png", help="decode .vpe/.vpea to RGBA PNG (one file per frame)")
    s.add_argument("files", nargs="+")
    s.add_argument("--out", help="output file or directory")
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--transparent-white", action="store_true",
                   help="treat RGB565 white 0xFFFF as alpha 0")
    s.set_defaults(fn=cmd_png)

    s = sub.add_parser("atlas", help="pack many .vpe/.vpea frames into one spritesheet + JSON")
    s.add_argument("files", nargs="*")
    s.add_argument("--dir", help="folder to scan recursively for .vpe/.vpea")
    s.add_argument("--out", required=True)
    s.add_argument("--json", help="metadata path")
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--transparent-white", action="store_true")
    s.set_defaults(fn=cmd_atlas)

    s = sub.add_parser("tileset", help="pack equal-size tiles into a grid sheet")
    s.add_argument("--dir", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--json")
    s.add_argument("--size", type=int, default=16, help="tile edge (0 = any)")
    s.add_argument("--cols", type=int)
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--no-recursive", action="store_true")
    s.add_argument("--transparent-white", action="store_true")
    s.set_defaults(fn=cmd_tileset)

    s = sub.add_parser("header", help="embed one still as C / Python / JS / JSON pixel data")
    s.add_argument("file")
    s.add_argument("--lang", choices=["c", "py", "js", "json"], default="c")
    s.add_argument("--name")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_header)

    s = sub.add_parser("batch-export", help="one atlas per gallery category folder")
    s.add_argument("--dir", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--scale", type=int, default=1)
    s.add_argument("--transparent-white", action="store_true")
    s.set_defaults(fn=cmd_batch_export)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except Exception as e:  # keep stdout machine-friendly
        print(f"ERROR  {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
