# User Guide

## Launch

| Method | Command |
|--------|---------|
| From source | `run.bat` or `python main.py` |
| Packaged EXE | `output\dist\VXP Pixel Editor\VXP Pixel Editor.exe` |

## Workspace

- **Left rail** — tools (Pencil, Eraser, Fill, Line, Rectangle, Filled Rect,
  Eyedropper) drawn from an icon font; hover any of them for its name and key
- **Center** — zoomable pixel canvas (grid, checker background, drop shadow)
- **Right** — Color, Brush, View, Document, Export panels
- **Status bar** — cursor `x,y`, tool, zoom, color, file path

Every control — rail, toolbar, panel buttons, palette swatches, gallery cards
and menu items — shows a hover title with its action and shortcut.

## Tools

| Tool | Key | Action |
|------|-----|--------|
| Pencil | `B` | Paint with current color |
| Eraser | `E` | Paint white (`#FFFF`) |
| Fill | `G` | Flood-fill a region |
| Line | `L` | Drag to draw a line |
| Rectangle | `U` | Stroke rectangle |
| Filled Rect | `R` | Filled rectangle |
| Eyedropper | `I` | Pick color from canvas |

Brush size: `1`–`5` or `[` `]`.

## View toggles

| Button | Shortcut | Meaning |
|--------|----------|---------|
| **BG** | `Ctrl+B` | Checker bed under the sprite |
| **No BG** | `Ctrl+Shift+B` | White pixels drawn as transparent |
| **Grid** | `Ctrl+G` | Pixel grid (visible when zoom ≥ 4) |
| Theme | `Ctrl+T` | Light ↔ Dark |

## Files

| Action | Menu | Default folder |
|--------|------|----------------|
| New canvas | File → New | sizes 16×16 … 240×320, or custom |
| Open `.vpe` / `.vpea` | File → Open | `Documents\VPE Pixel` |
| Import image | File → Import | PNG / JPG / BMP → RGB565 |
| Save `.vpe` / `.vpea` | File → Save | `Documents\VPE Pixel` |
| Export BMP/PNG | File → Export | `Documents\VPE Pixel\exports` |

## Viewport

| Input | Effect |
|-------|--------|
| Scroll wheel | Zoom in / out |
| Right-drag / Middle-drag | Pan |
| Double-click canvas | Fit to window |
| `Ctrl+0` / `Ctrl+=` / `Ctrl+-` | Fit / Zoom in / Zoom out |

## Undo

- `Ctrl+Z` — undo (one stroke / fill / shape = one step)
- `Ctrl+Shift+Z` or `Ctrl+Y` — redo
- History keeps up to 80 steps

## Animation

Every canvas can hold up to **256 frames** of the same size. A one-frame
document behaves exactly like before — use **Add Frame** to start animating.

The timeline bar sits under the canvas: transport (previous, play, next, stop),
frame tools (add, duplicate, delete, move back / forward), speed in fps
(1 … 30, delay = 1000 ÷ fps), loop, onion skin + how many frames to ghost, and
a strip of live thumbnails of every frame. Click a thumbnail to edit it.

| Action | Shortcut |
|--------|----------|
| Play / pause | `Space` |
| Stop and keep the frame | `Esc` |
| Next / previous frame | `.` / `,` |
| Add empty frame after the current one | `Ctrl+Alt+N` |
| Duplicate the current frame | `Ctrl+D` |
| Delete the current frame | `Ctrl+Shift+K` |
| Move the current frame back / forward | `Ctrl+Alt+Left` / `Ctrl+Alt+Right` |
| Onion skin | `Ctrl+O` |
| Export every frame as one PNG strip | `Ctrl+Alt+P` |

- **Onion skin** ghosts the neighbouring frames behind the one you paint, faded
  by distance, so walk cycles line up. It pauses automatically while playing.
- Undo and redo remember which frame a change was made on and jump back to it.
- Painting only ever touches the current frame.

### Saving animations

| Situation | Behaviour |
|-----------|-----------|
| More than one frame, `.vpea` path | Writes the whole animation |
| More than one frame, `.vpe` path | `Ctrl+S` opens Save As — `.vpe` stores one frame only |
| Single frame | `.vpe` as before, byte-compatible with LuaS30 |
| Open dialog | Accepts `*.vpe` and `*.vpea`; the gallery labels animations `SPRITE · 5F` |

The **Export PNG Strip** action writes the frames side by side into one PNG with
white keyed out — a ready spritesheet for a game engine.

To watch a whole folder without opening files one by one, run
`python tools/play_animations.py`. It loads every `.vpea` under the sprite
library into this same window, starts the timeline's own playback, checks that
each frame really gets painted, and writes `play_<scene>.gif` +
`playback_filmstrip.png` into `Documents\VPE Pixel\exports\playback`
(`--dir` picks another folder, `--out` another destination).

`python tools/make_effect_anim.py` fills `sprite\effect\` with seven reusable
skill effects (fireball, explosion, lightning, cast circle, ice shards, poison
cloud, heal sparkle) and writes their strips to `exports\effect\`; the knight
set in `tools/make_knight_anim.py` does the same for character animation.

`python tools/make_player_anim.py` does it for the player: it redraws the hero
from the existing `td_hero_*` stills as 28 scenes — `hero_down_idle`,
`hero_right_attack`, `hero_up_die` and so on, four directions times seven
actions — into `sprite\characters\player\`, with per-scene strips in
`exports\player\` and one review sheet per direction. `--only down,right`
limits the run to the directions you are checking.

`python tools/make_dragon_anim.py` does it for the boss: eight 48×48 scenes —
`dragon_idle`, `dragon_walk`, `dragon_fly`, `dragon_bite`, `dragon_breath`,
`dragon_slam`, `dragon_hurt`, `dragon_die` — written to
`sprite\enemies\boss\`, with per-scene strips plus an atlas in `exports\boss\`
and one contact sheet (`exports\boss_sheet_all.png`) for the whole set. Because
the boss is built from parts (tail, legs, torso, wings, neck, head) and outlined
in one pass at the end, `--only breath,slam` is the usual way to check a single
attack without redrawing the sheet.

`python tools/make_golem_anim.py` does it for the second boss: the same eight
scene slots under `golem_` — `golem_idle`, `golem_walk`, `golem_roar`,
`golem_slam`, `golem_boulder`, `golem_beam`, `golem_hurt`, `golem_die` — into
`sprite\enemies\boss\` and `exports\golem_sheet_all.png`. It reuses the dragon's
canvas and outline pass, so both bosses pack into one 74-frame atlas.

`python tools/make_wizard_anim.py` adds the third boss — `wizard_idle`,
`wizard_walk`, `wizard_cast`, `wizard_bolt`, `wizard_blizzard`, `wizard_freeze`,
`wizard_hurt`, `wizard_die` (40 frames) into the same folder, taking the atlas to
114 frames. Its body is cloth rather than rock, so the same `rim()` union pass
needs the robe, the fur trim and the hood each in their own tone or they melt
into one silhouette.

`python tools/make_slime_anim.py` is the fourth (`slime_idle`, `_hop`, `_slide`,
`_attack`, `_split`, `_spit`, `_hurt`, `_die`, 36 frames). It has no limbs at all:
one `body()` shape function walks the rows and derives each row's half-width from
a superellipse plus wobble harmonics, so every scene deforms the same creature
instead of redrawing it.

`python tools/make_scorpion_anim.py` is the fifth and the only horizontal boss of
the set (`scorpion_idle`, `_walk`, `_sting`, `_pinch`, `_venom`, `_burrow`,
`_hurt`, `_die`, 38 frames, atlas 188). The animal is drawn by one `scorpion()`
pose function, and the tail is the interesting parameter: `curl` is not a scale
but an *amount of turn*, so each of the five joints adds a share of a total sweep
angle and raising or lowering the tail walks the barb along one arc. That is what
keeps the sting readable without a single per-frame coordinate. A union `rim()`
pass is unforgiving here — it separates parts only by *colour*, and a scorpion is
nothing but segments — so the tail plates alternate lit and mid chitin with a
dark ring at each joint, and the claws, legs, telson bulb and sand each own a
tone. Sand, venom and the eyes stay outside the fill set: dust must not be
outlined, and the glow is painted after the rim.

## Tips

- RGB565 has no alpha — **No BG** is a *preview* of white-as-transparent.
- For real transparency in PNG, export from a tool that has alpha, or keep
  the background color intentional in the sprite.
- Dimensions up to **640×640** are valid for `.vpe`.
- Right panel **Swap** exchanges foreground and background chips.

## Folders on disk

```
Documents\VPE Pixel\            .vpe projects
Documents\VPE Pixel\exports\    BMP / PNG
%APPDATA%\VXP Pixel Editor\     settings.ini, autosave.vpe
```

The four category folders are created on first run and the gallery reads
everything below them, so you can group freely:

```
sprite\characters\player\       tile\topdown\terrain\        texture\background\parallax\
sprite\effect\                  tile\side\platform\          texture\ui\
sprite\enemies\                 tile\side\hazard\
sprite\items\icons\             sprite\vfx\particles\        titleset\
```

A file's category comes from the nearest of those four folder names in its path,
never from how deep it sits. Full layout and rationale: [ASSET_TAXONOMY.md](ASSET_TAXONOMY.md).
