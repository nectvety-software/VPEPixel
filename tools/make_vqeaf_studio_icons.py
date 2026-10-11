"""Draw the VQEAF Theme Studio icon set with the VXP Pixel Editor VPE565 pipeline.

Why this file exists
--------------------
The theme studio used to render its key decorations, keypad symbols and toolbar
buttons as **emoji** (U+1F300..U+1FAFF and friends). Emoji render differently on
every OS/browser, cannot be recoloured, and are not pixel art. This tool replaces
them with real 12x12 sprites drawn here, in the same VPE565 pipeline as the rest
of the pixel art:

    .vpe (source of truth, RGB565)  ->  PNG RGBA (white keyed to alpha)

The studio then embeds the PNGs as data-URIs (see
`VQEAF-Theme-Studio/tools/import_vpe_icons.mjs`).

Sizes
-----
Everything is authored at **12x12** so the studio can render it at 1x (12px) on
a key/toolbar and 2x (24px) in the Button Builder preview — integer scales only,
otherwise pixel art gets uneven pixels.

Transparency rule
-----------------
VPE565 has no alpha. `0xFFFF` is the editor's transparency key, so **no glyph may
use pure white** or it punches a hole. Every "white" here is `#FFF6E8` (packs to
0xFFBD). The generator asserts this and fails loudly if a design breaks the rule.

Writes
------
  Documents/VPE Pixel/tile/vqeaf_studio/<name>_12.vpe
  Documents/VPE Pixel/exports/vqeaf_studio/<name>.png        RGBA, white keyed
  Documents/VPE Pixel/exports/vqeaf_studio/_sheet.png        contact sheet

Run from the Pixel_Editor root:
  python tools/make_vqeaf_studio_icons.py
  python tools/make_vqeaf_studio_icons.py --sheet-only
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vpx_editor.vpe import rgb_to_565, save_vpe  # noqa: E402

SIZE = 12
CLEAR = 0xFFFF  # VPE transparent key — must never be used as an ink colour

# --- palette -----------------------------------------------------------------
# Single-char tokens so the art stays reviewable as plain text.
# NB: no token may pack to 0xFFFF (asserted below).
TOKENS: Dict[str, Tuple[int, int, int]] = {
    ".": (0, 0, 0),            # CLEAR sentinel, handled specially
    "#": (255, 246, 232),      # near-white ink  (0xFFBD, NOT 0xFFFF)
    "+": (200, 206, 220),      # light grey
    "g": (138, 144, 160),      # grey
    "K": (46, 40, 54),         # dark grey
    "k": (20, 16, 24),         # near black
    "y": (255, 210, 63),       # yellow
    "Y": (184, 137, 15),       # dark yellow
    "a": (255, 200, 87),       # amber
    "o": (255, 154, 46),       # orange
    "O": (194, 94, 16),        # dark orange
    "r": (226, 58, 80),        # red
    "R": (142, 18, 38),        # dark red
    "m": (240, 98, 184),       # magenta / pink
    "M": (142, 30, 100),       # dark magenta
    "p": (160, 92, 216),       # purple
    "P": (78, 36, 114),        # dark purple
    "n": (76, 194, 76),        # green
    "N": (30, 122, 46),        # dark green
    "l": (155, 232, 92),       # lime
    "c": (76, 216, 232),       # cyan
    "C": (26, 126, 150),       # dark cyan
    "b": (74, 124, 240),       # blue
    "B": (30, 62, 158),        # dark blue
    "w": (138, 90, 46),        # brown
    "W": (78, 46, 18),         # dark brown
    "s": (240, 200, 154),      # tan / skin
}

PAL: Dict[str, int] = {
    k: CLEAR if k == "." else rgb_to_565(*v) for k, v in TOKENS.items()
}


class Img:
    """Minimal RGB565 canvas (same contract as tools/make_samples.Img)."""

    def __init__(self, w: int, h: int, fill: int = CLEAR) -> None:
        self.w, self.h = w, h
        self.px: List[int] = [fill] * (w * h)

    def set(self, x: int, y: int, c: int) -> None:
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def get(self, x: int, y: int) -> int:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y * self.w + x]
        return CLEAR

    def rect(self, x: int, y: int, w: int, h: int, c: int) -> None:
        for j in range(int(h)):
            for i in range(int(w)):
                self.set(x + i, y + j, c)

    def frame(self, x: int, y: int, w: int, h: int, c: int, t: int = 1) -> None:
        for i in range(w):
            for k in range(t):
                self.set(x + i, y + k, c)
                self.set(x + i, y + h - 1 - k, c)
        for j in range(h):
            for k in range(t):
                self.set(x + k, y + j, c)
                self.set(x + w - 1 - k, y + j, c)

    def stamp(self, x: int, y: int, rows: Sequence[str]) -> None:
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                c = PAL.get(ch)
                if c is None or c == CLEAR:
                    continue
                self.set(x + i, y + j, c)


# ---------------------------------------------------------------------------
# 12x12 art. Every row MUST be exactly 12 chars — validated at load time.
# ---------------------------------------------------------------------------

ART: Dict[str, List[str]] = {
    # --- key decorations ---------------------------------------------------
    "leaf": [
        "............",
        ".....##.....",
        "....#nn#....",
        "...#nnnn#...",
        "..#nnNnnn#..",
        ".#nnNnnnnn#.",
        ".#nNnnnnnn#.",
        ".#nNnnnnnn#.",
        "..#nnNnnn#..",
        "...#nnnn#...",
        "....####....",
        "............",
    ],
    "flower": [
        "............",
        "..##....##..",
        ".#mm#..#mm#.",
        ".#mm#..#mm#.",
        "..##.##.##..",
        "...##yy##...",
        "..##yyyy##..",
        "...##yy##...",
        "..##.##.##..",
        ".#mm#..#mm#.",
        ".#mm#..#mm#.",
        "..##....##..",
    ],
    "cloud": [
        "............",
        "............",
        "....####....",
        "..##++++##..",
        ".#++++++++#.",
        ".#++++++++#.",
        "#++++++++++#",
        "#++++++++++#",
        ".#gg++++gg#.",
        "..########..",
        "............",
        "............",
    ],
    "star": [
        "............",
        ".....##.....",
        ".....##.....",
        "....####....",
        ".####yyyy##.",
        "..##yyyyyy#.",
        "...##yyyy#..",
        "...##yyyy#..",
        "..###..###..",
        ".###....###.",
        ".##......##.",
        "............",
    ],
    "gem": [
        "............",
        "....####....",
        "..##cccc##..",
        ".#ccccccccc#",
        ".#cCccccCc#.",
        ".#ccCccCcc#.",
        "..#ccCCcc#..",
        "..#cCccCc#..",
        "...#cCCc#...",
        "...#cCc#....",
        "....#c#.....",
        ".....#......",
    ],
    "sparkle": [
        "............",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "..##.##.##..",
        "..########..",
        "##########..",
        "..########..",
        "..##.##.##..",
        ".....##.....",
        ".....##.....",
        "............",
    ],
    # Lid + rim seam + gold lock. Without the seam and lock this rendered as a
    # plain rounded rectangle and was indistinguishable from `keypadbg`.
    "chest": [
        "............",
        "...######...",
        "..#ssssss#..",
        ".#ssssssss#.",
        ".#ssssssss#.",
        "############",
        ".#wwwwwwww#.",
        ".#wwwyywww#.",
        ".#wwwyywww#.",
        ".#wwwwwwww#.",
        "..########..",
        "............",
    ],
    "slime": [
        "............",
        "............",
        "............",
        "....####....",
        "..##nnnn##..",
        ".#nnlnnnnn#.",
        "#nnlnnnnnnn#",
        "#nnnnnnnnnn#",
        "#nNnnnnnnNn#",
        "#nNNnnnnNNn#",
        ".#NNNNNNNN#.",
        "..########..",
    ],
    "pumpkin": [
        "............",
        ".....##.....",
        "....#NN#....",
        "..##oooo##..",
        ".#oooooooo#.",
        "#oooYooYooo#",
        "#ooYoooooYo#",
        "#oooOooOooo#",
        "#ooOooooOoo#",
        ".#ooOooOoo#.",
        "..##OOOO##..",
        "....####....",
    ],
    "bat": [
        "............",
        "............",
        ".##......##.",
        "#pp#....#pp#",
        "#ppp####ppp#",
        "#pppppppppp#",
        "#pPpppppPpp#",
        ".#ppp##ppp#.",
        "..#pp##pp#..",
        "...#p#.#p#..",
        "....#...#...",
        "............",
    ],
    # Radial web. Hand-drawn: the first attempt was a set of diagonal dashes that
    # rendered as a striped egg. A web only reads if it has a closed outer ring,
    # an inner ring and spokes running between them, so the outline is continuous.
    "web": [
        ".....##.....",
        "...##..##...",
        "..#......#..",
        ".#.######.#.",
        ".#.##..##.#.",
        "#..#.##.#..#",
        "#..#.##.#..#",
        ".#.##..##.#.",
        ".#.######.#.",
        "..#......#..",
        "...##..##...",
        ".....##.....",
    ],
    "ghost": [
        "............",
        "....####....",
        "..##++++##..",
        ".#++++++++#.",
        ".#+kk++kk+#.",
        ".#+kk++kk+#.",
        ".#++++++++#.",
        ".#+++kk+++#.",
        ".#++++++++#.",
        ".#++++++++#.",
        ".#+#+##+#+#.",
        "..#.#..#.#..",
    ],
    # Shield, not a dome: `slime` and `led` are already domes, so a fourth dome
    # would make the three layer icons indistinguishable in the layer list.
    "badge": [
        "............",
        "............",
        "..########..",
        ".#++++++++#.",
        ".#++++++++#.",
        ".#++++++++#.",
        ".#++++++++#.",
        ".#++++++++#.",
        "..#++++++#..",
        "...#++++#...",
        "....#++#....",
        ".....##.....",
    ],
    # --- keypad / phone ----------------------------------------------------
    "tri_up": [
        "............",
        "............",
        "............",
        ".....##.....",
        "....####....",
        "...######...",
        "..########..",
        ".##########.",
        "############",
        "............",
        "............",
        "............",
    ],
    "tri_down": [
        "............",
        "............",
        "............",
        "############",
        ".##########.",
        "..########..",
        "...######...",
        "....####....",
        ".....##.....",
        "............",
        "............",
        "............",
    ],
    # Apex left, vertical base on the right. The original was 6px wide against 11
    # tall, so it read as a slim arrow rather than a triangle; widened to 7px and
    # made vertically symmetric so it reads as a solid glyph at 12px.
    "tri_left": [
        "............",
        ".........#..",
        "........##..",
        ".......###..",
        "......####..",
        ".....#####..",
        "...#######..",
        ".....#####..",
        "......####..",
        ".......###..",
        "........##..",
        ".........#..",
    ],
    "tri_right": [
        "............",
        "..#.........",
        "..##........",
        "..###.......",
        "..####......",
        "..#####.....",
        "..#######...",
        "..#####.....",
        "..####......",
        "..###.......",
        "..##........",
        "..#.........",
    ],
    "call": [
        "............",
        "............",
        "..####......",
        ".#nnnn#.....",
        ".#nnnn##....",
        ".#nnnnn#....",
        "..#nnnn##...",
        "...##nnnn#..",
        ".....#nnnn#.",
        "......#nnn#.",
        ".......####.",
        "............",
    ],
    "menu_lines": [
        "............",
        "............",
        "............",
        "############",
        "............",
        "............",
        "############",
        "............",
        "............",
        "############",
        "............",
        "............",
    ],
    "camera": [
        "............",
        "............",
        "...####.....",
        "..######....",
        "############",
        "#++++++++++#",
        "#++#####+++#",
        "#++#ccc#+++#",
        "#++#cCc#+++#",
        "#++#####+++#",
        "#++++++++++#",
        "############",
    ],
    "dash": [
        "............",
        "............",
        "............",
        "............",
        "............",
        "............",
        "..########..",
        "..########..",
        "............",
        "............",
        "............",
        "............",
    ],
    # Two rounded lobes with a 2px notch. At 12px a geometrically correct
    # lemniscate is impossible — a 1px waist vanishes once the sprite is drawn
    # at 12px, so the notch has to be two columns wide to survive.
    "infinity": [
        "............",
        "............",
        "...##..##...",
        "..###..###..",
        ".####..####.",
        ".####..####.",
        ".####..####.",
        ".####..####.",
        "..###..###..",
        "...##..##...",
        "............",
        "............",
    ],
    "shift": [
        "............",
        "............",
        ".....##.....",
        "....####....",
        "...######...",
        "..########..",
        ".##########.",
        "############",
        "....####....",
        "....####....",
        "....####....",
        "............",
    ],
    # --- studio UI ---------------------------------------------------------
    # Pips are K (dark), not # (near-white). The first version drew pips as `#`
    # on a `+` face — near-white on light grey, i.e. almost no contrast, so the
    # die rendered as a plain square with no pips at all.
    "dice": [
        "............",
        "............",
        "..########..",
        ".#++++++++#.",
        ".#+K++++K+#.",
        ".#++++++++#.",
        ".#+++KK+++#.",
        ".#++++++++#.",
        ".#+K++++K+#.",
        ".#++++++++#.",
        "..########..",
        "............",
    ],
    "undo": [
        "............",
        "............",
        "............",
        "...##.......",
        "..###.......",
        ".#########..",
        "###########.",
        "..###....###",
        "...##....###",
        ".........+#.",
        ".......###..",
        "............",
    ],
    "redo": [
        "............",
        "............",
        "............",
        ".......##...",
        ".......###..",
        "..#########.",
        ".###########",
        "###....###..",
        "###....##...",
        ".+#.........",
        "..###.......",
        "............",
    ],
    # Ribs are K (dark) for the same contrast reason as the die pips.
    "trash": [
        "............",
        "....####....",
        "..########..",
        ".#++++++++#.",
        "..########..",
        "..#+K+K+K+#.",
        "..#+K+K+K+#.",
        "..#+K+K+K+#.",
        "..#+K+K+K+#.",
        "..#+K+K+K+#.",
        "..########..",
        "............",
    ],
    # Ring open at the top-left / top-right with a solid arrowhead in the gap.
    # The first version used a `####`/`#..#`/`####` block for the head, which is
    # a "C" shape, not an arrowhead — it read as a ring with a bite taken out.
    "rotate_ccw": [
        "............",
        "..#.####....",
        "..###...##..",
        ".##......##.",
        "#.........#.",
        "#.........#.",
        "#.........#.",
        ".#........#.",
        "..##....##..",
        "....####....",
        "............",
        "............",
    ],
    "rotate_cw": [
        "............",
        "....####.#..",
        "..##...###..",
        ".##......##.",
        "#.........#.",
        "#.........#.",
        "#.........#.",
        ".#........#.",
        "..##....##..",
        "....####....",
        "............",
        "............",
    ],
    # Mirror-axis motif: two shapes pointing at each other across a dashed axis.
    # An arrow-based design was ambiguous — flip_h looked like arrow_left/right
    # and flip_v was pixel-identical to move_down. The dashed axis is the whole
    # point of the icon, so it has to be visible.
    "flip_h": [
        "............",
        "......#.....",
        ".#....#...#.",
        ".##...#..##.",
        ".###..#..###",
        ".####.#.####",
        ".####.#.####",
        ".###..#..###",
        ".##...#..##.",
        ".#....#...#.",
        "......#.....",
        "............",
    ],
    "flip_v": [
        "............",
        ".##########.",
        "..########..",
        "...######...",
        "....####....",
        ".....##.....",
        "#.#.#.#.#.#.",
        ".....##.....",
        "....####....",
        "...######...",
        "..########..",
        ".##########.",
    ],
    "move_up": [
        "............",
        "............",
        ".....##.....",
        "....####....",
        "...######...",
        "..########..",
        ".##########.",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "............",
    ],
    "move_down": [
        "............",
        "............",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        ".##########.",
        "..########..",
        "...######...",
        "....####....",
        ".....##.....",
        "............",
    ],
    "close": [
        "............",
        "............",
        ".##......##.",
        "###......###",
        ".###....###.",
        "..###..###..",
        "...######...",
        "..###..###..",
        ".###....###.",
        "###......###",
        ".##......##.",
        "............",
    ],
    "arrow_left": [
        "............",
        "............",
        "......##....",
        ".....##.....",
        "....##......",
        "...##.......",
        "..##########",
        "..##########",
        "...##.......",
        "....##......",
        ".....##.....",
        "......##....",
    ],
    "arrow_right": [
        "............",
        "............",
        "....##......",
        ".....##.....",
        "......##....",
        ".......##...",
        "##########..",
        "##########..",
        ".......##...",
        "......##....",
        ".....##.....",
        "....##......",
    ],
    "plus": [
        "............",
        "............",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "..########..",
        "..########..",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "............",
        "............",
    ],
    "reset": [
        "............",
        "....####....",
        "..##....##..",
        ".#........#.",
        "#..........#",
        "#..........#",
        "#.......####",
        ".#......#...",
        "..##....#...",
        "....####....",
        "............",
        "............",
    ],
    # --- component palette / layer icons -----------------------------------
    # The four layer icons below were previously all "rectangle with a pattern"
    # and at 12px they were indistinguishable in the layer list. Each now has a
    # distinct silhouette: keys on transparent (keypad), a framed key plate
    # (keyboard), a dark plate with dimmed keys (keypadbg), a monitor on a stand
    # (screen), and a nested frame (frame).
    "keyboard": [
        "............",
        "............",
        ".##########.",
        "#++++++++++#",
        "#+KK+KK+KK+#",
        "#++++++++++#",
        "#+KK+KK+KK+#",
        "#++++++++++#",
        "#+++KKKK+++#",
        "#++++++++++#",
        ".##########.",
        "............",
    ],
    "frame": [
        "............",
        "############",
        "#..........#",
        "#.########.#",
        "#.#......#.#",
        "#.#......#.#",
        "#.#......#.#",
        "#.#......#.#",
        "#.########.#",
        "#..........#",
        "############",
        "............",
    ],
    "screen": [
        "............",
        "............",
        ".##########.",
        "#KKKKKKKKKK#",
        "#K++++++++K#",
        "#K++++++++K#",
        "#K++++++++K#",
        "#KKKKKKKKKK#",
        ".##########.",
        "....####....",
        "..########..",
        "............",
    ],
    "keypad": [
        "............",
        "............",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "..##.##.##..",
        "............",
        "............",
    ],
    "keypadbg": [
        "............",
        "............",
        ".##########.",
        "#KKKKKKKKKK#",
        "#K++K++K++K#",
        "#KKKKKKKKKK#",
        "#K++K++K++K#",
        "#KKKKKKKKKK#",
        "#K++K++K++K#",
        "#KKKKKKKKKK#",
        ".##########.",
        "............",
    ],
    # Bulb with a specular highlight, so it does not read as another `slime` dome.
    "led": [
        "............",
        "............",
        "....####....",
        "..##++++##..",
        ".#++#+++++#.",
        ".#+#++++++#.",
        ".#++++++++#.",
        ".#++++++++#.",
        "..##++++##..",
        "....####....",
        "............",
        "............",
    ],
    "decoration": [
        "............",
        ".....##.....",
        ".....##.....",
        ".....##.....",
        "..##.##.##..",
        "..########..",
        "############",
        "..########..",
        "..##.##.##..",
        ".....##.....",
        ".....##.....",
        "............",
    ],
    # Battery. The studio drew this as the text glyph '▮' in both the DOM and the
    # exported PNG; it is an icon, so it belongs in the set like the rest.
    "battery": [
        "............",
        "............",
        "............",
        "..########..",
        ".#++++++++#.",
        ".#+KK+KK++##",
        ".#+KK+KK++##",
        ".#++++++++#.",
        "..########..",
        "............",
        "............",
        "............",
    ],
}

# NB: there used to be a MONO table here mapping icons to an ink override. It was
# never read by draw(), so it silently did nothing while looking authoritative.
# Removed rather than wired up: every sprite now states its own colours inline,
# and the studio tints via CSS when it needs a themed colour.


def validate_art() -> None:
    bad: List[str] = []
    for name, rows in ART.items():
        if len(rows) != SIZE:
            bad.append(f"{name}: {len(rows)} rows (want {SIZE})")
            continue
        for j, row in enumerate(rows):
            if len(row) != SIZE:
                bad.append(f"{name} row {j}: {len(row)} chars (want {SIZE})")
    if bad:
        raise SystemExit("ART invalid:\n  " + "\n  ".join(bad))


def validate_orientation() -> None:
    """Directional sprites must actually point the way their name says.

    Which side the ink mass sits on depends on the glyph family, and getting this
    backwards is invisible until you look at a render — a `tri_left` that points
    right still looks like a perfectly good triangle.

      * solid triangles carry their mass at the BASE, i.e. opposite the tip
      * arrows (and the move_* glyphs) carry it on the TIP/shaft side

    So each entry states the axis and the expected sign of (centroid - midpoint).
    """
    spec: List[Tuple[str, str, int]] = [
        ("tri_up", "y", +1),
        ("tri_down", "y", -1),
        ("tri_left", "x", +1),
        ("tri_right", "x", -1),
        ("move_up", "y", -1),
        ("move_down", "y", +1),
        ("arrow_left", "x", -1),
        ("arrow_right", "x", +1),
    ]
    bad: List[str] = []
    for name, axis, want in spec:
        rows = ART[name]
        if axis == "x":
            counts = [sum(1 for r in rows if r[x] != ".") for x in range(SIZE)]
        else:
            counts = [sum(1 for ch in r if ch != ".") for r in rows]
        live = [i for i, c in enumerate(counts) if c]
        total = sum(counts)
        centroid = sum(i * counts[i] for i in live) / total
        mid = (live[0] + live[-1]) / 2
        got = 1 if centroid > mid else (-1 if centroid < mid else 0)
        if got != want:
            bad.append(f"{name}: centroid {axis}={centroid:.2f} vs mid {mid:.1f} "
                       f"-> mass sign {got:+d}, want {want:+d} (points the wrong way)")
    if bad:
        raise SystemExit("orientation invalid:\n  " + "\n  ".join(bad))


def validate_no_white() -> None:
    """No glyph pixel may equal the VPE transparency key."""
    offenders: List[str] = []
    for tok, val in TOKENS.items():
        if tok == ".":
            continue
        if rgb_to_565(*val) == CLEAR:
            offenders.append(f"token {tok!r} -> 0xFFFF")
    if offenders:
        raise SystemExit("palette breaks the white key:\n  " + "\n  ".join(offenders))


def draw(name: str) -> Img:
    img = Img(SIZE, SIZE)
    img.stamp(0, 0, ART[name])
    return img


def encode_png_rgba(path: Path, w: int, h: int, pixels: Sequence[int]) -> None:
    """Write an 8-bit RGBA PNG with the VPE white key turned into alpha 0.

    Stdlib only — vpx_editor.vpe.save_png needs Qt, and this tool must run in a
    bare `python` environment (same reasoning as tools/make_vqeaf_icons.py).
    """
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0
        for x in range(w):
            c = pixels[y * w + x]
            if c == CLEAR:
                raw += b"\x00\x00\x00\x00"
                continue
            r = ((c >> 11) & 0x1F) * 255 // 31
            g = ((c >> 5) & 0x3F) * 255 // 63
            b = (c & 0x1F) * 255 // 31
            raw += bytes((r, g, b, 255))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def build_sheet(names: Sequence[str], cell: int = 20, cols: int = 8, scale: int = 1) -> Img:
    rows = (len(names) + cols - 1) // cols
    sheet = Img(cols * cell, rows * cell, rgb_to_565(18, 20, 28))
    for i, name in enumerate(names):
        im = draw(name)
        ox = (i % cols) * cell + (cell - SIZE * scale) // 2
        oy = (i // cols) * cell + (cell - SIZE * scale) // 2
        for y in range(SIZE):
            for x in range(SIZE):
                c = im.get(x, y)
                if c != CLEAR:
                    for sy in range(scale):
                        for sx in range(scale):
                            sheet.set(ox + x * scale + sx, oy + y * scale + sy, c)
    return sheet


def main() -> int:
    validate_art()
    validate_orientation()
    validate_no_white()

    names = list(ART.keys())
    home = Path.home()
    vpe_dir = home / "Documents" / "VPE Pixel" / "tile" / "vqeaf_studio"
    out_dir = home / "Documents" / "VPE Pixel" / "exports" / "vqeaf_studio"
    vpe_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if "--sheet-only" not in sys.argv:
        for name in names:
            img = draw(name)
            save_vpe(vpe_dir / f"{name}_{SIZE}.vpe", SIZE, SIZE, img.px)
            encode_png_rgba(out_dir / f"{name}.png", SIZE, SIZE, img.px)
        print(f"OK {len(names)} icons -> {vpe_dir}")
        print(f"OK {len(names)} png   -> {out_dir}")

    sheet = build_sheet(names)
    encode_png_rgba(out_dir / "_sheet.png", sheet.w, sheet.h, sheet.px)
    print(f"sheet {out_dir / '_sheet.png'}  ({sheet.w}x{sheet.h}, {len(names)} icons)")

    # Full-colour magnified sheet. tools/inspect_art.py renders silhouettes in a
    # single ink colour, which is right for judging shape but useless for judging
    # palette — this one keeps the real token colours so hue collisions show up.
    big = build_sheet(names, cell=SIZE * 6 + 8, cols=8, scale=6)
    encode_png_rgba(out_dir / "_sheet_6x.png", big.w, big.h, big.px)
    print(f"sheet {out_dir / '_sheet_6x.png'}  ({big.w}x{big.h})")

    # Self-check. NB: CLEAR *is* 0xFFFF, i.e. the same word as pure white, so you
    # cannot detect "white ink" by scanning packed pixels — the background is
    # indistinguishable from it. The real guard is validate_no_white(), which
    # checks every palette token. Here we only confirm the palette is sound and
    # report how much of each sprite is keyed background.
    keyed = sum(im.px.count(CLEAR) for im in (draw(n) for n in names))
    total = len(names) * SIZE * SIZE
    print(f"palette tokens checked: {len(TOKENS) - 1} (none packs to 0xFFFF)")
    print(f"keyed background pixels: {keyed}/{total} ({100 * keyed / total:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
