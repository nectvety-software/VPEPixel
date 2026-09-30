# VXP Pixel Editor (Python / PySide6)

Professional pixel-art editor with native **VPE565** (`.vpe`) project support.

Inspired by the LuaS30 **VXP Pixel Editor** (`VXP_Pixel_Editor`) for Nokia S30+ / MediaTek MRE,
rebuilt as an enterprise-style desktop app with Qt for Python.

**Docs:** see [`docs/`](docs/README.md) · Product prompt [`PROMPT.md`](PROMPT.md) · Agent guide [`SKILLS.md`](SKILLS.md)

## Features

- **Native `.vpe` (VPE565)** open / save — byte-compatible with the LuaS30 editor
- RGB565 canvas + classic 16-color PixlCreate palette
- Tools: Pencil, Eraser, Fill (span flood), Line, Rectangle, Filled Rectangle, Eyedropper
- Brush size 1–5, undo / redo transactions
- Zoomable pixel canvas with grid, pan (middle/right drag), fit-to-window
- Export **BMP** (24-bit) and **PNG**; import **PNG / JPG / BMP**
- **Animation** — up to 256 frames per canvas in the native `.vpea` (VPEA01) container:
  timeline strip of live thumbnails, add / duplicate / delete / reorder frames, fps + loop,
  `Space` playback, onion skin over the neighbouring frames, per-frame undo history,
  **Export PNG Strip** for a ready spritesheet, and `python tools/play_animations.py`
  to batch-preview every `.vpea` as an animated GIF (`.vpe` stays single-frame and compatible)
- **Asset collection (gallery)** — browse game assets by category: `titleset`, `sprite`, `texture`, `tile`
  (recursive scan of `Documents\VPE Pixel` to 4 levels, so taxonomy sub-folders like
  `sprite/characters/player/` group without breaking classification; pixel-crisp thumbnails
  with white-as-transparent for sprites/tiles, search, duplicate / rename / move /
  delete-to-Recycle-Bin, one-click PNG/JPG/BMP import)
- **Sample asset generator** — `python tools/make_samples.py` draws 285 ready-made game assets
  (9 title screens, 172 sprites/FX frames, 19 texture sheets, 85 map tiles) into the gallery folders,
  covering the arctic "Snow Base Defense" set and the top-down / side-scroller taxonomy of
  [`docs/ASSET_TAXONOMY.md`](docs/ASSET_TAXONOMY.md)
- **Animation sample generator** — `python tools/make_knight_anim.py` draws the sword-and-shield
  knight test set (idle 4 / walk 4 / attack 8 / block 3 / skill 6 = 25 frames in 5 `.vpea`
  animations, plus 3 standalone slash, shield-flash and shockwave FX sequences) and
  scaled-up contact-sheet PNGs for review
- **Effect animation generator** — `python tools/make_effect_anim.py` draws 7 reusable skill
  effects (fireball 6 / explosion 7 / lightning 5 / cast circle 8 / ice shards 5 / poison
  cloud 6 / heal sparkle 5 = 42 frames) as `.vpea` into `Documents\VPE Pixel\sprite\effect\`,
  exporting per-scene strips to `exports\effect\` and a review sheet to `exports\effect_sheet_all.png`
- **Player animation generator** — `python tools/make_player_anim.py` turns the shipped 16×16
  hero stills into 28 playable `.vpea` scenes (4 directions × idle 4 / walk 4 / run 4 /
  attack 4 / cast 5 / hurt 3 / die 5 = 116 frames) in `Documents\VPE Pixel\sprite\characters\player\`,
  with strips in `exports\player\` and one review sheet per direction
- **Boss animation generator** — `python tools/make_dragon_anim.py` draws the dragon boss as
  8 `.vpea` scenes at 48×48 (idle 4 / walk 4 / fly 4 / bite 4 / breath 6 / slam 5 / hurt 3 /
  die 6 = 36 frames) in `Documents\VPE Pixel\sprite\enemies\boss\`, with strips and an atlas in
  `exports\boss\` and one contact sheet for the whole set. `python tools/make_golem_anim.py`
  adds the stone golem the same way (idle 4 / walk 4 / roar 4 / slam 5 / boulder 6 / beam 6 /
  hurt 3 / die 6 = 38 frames), `python tools/make_slime_anim.py` the slime king
  (idle 4 / hop 4 / slide 4 / attack 4 / split 5 / spit 6 / hurt 3 / die 6 = 36 frames),
  `python tools/make_wizard_anim.py` the ice wizard
  (idle 4 / walk 4 / cast 5 / bolt 6 / blizzard 6 / freeze 6 / hurt 3 / die 6 = 40 frames)
  and `python tools/make_scorpion_anim.py` the sand scorpion, the only horizontal boss of the
  five (idle 4 / walk 4 / sting 5 / pinch 4 / venom 6 / burrow 6 / hurt 3 / die 6 = 38 frames).
  Together: 40 scenes, 188 frames, one 659×735 atlas
- **Fnynn map + sprite generator** — `python tools/make_fnynn_map.py` redraws the whole
  top-down farm-RPG asset set for the `Fnynn` MRE game as 92 procedural sprites
  (15 tiles `t_*` 16×16 + 77 sprites: 4 crops × 4 stages, trees/rocks/tufts/mushrooms,
  seasonal flowers + berries, farmstead `h_*`, player 3 classes × 3 directions × 2 steps,
  4 mobs × 2 frames, NPCs, items, `menu_bg`) into
  `Documents\VPE Pixel\fnynn_map\tile\` and `...\sprite\` as `.png` + editable `.vpe`,
  plus a labelled contact sheet and a 240×320 mock scene for review.
  `python tools/make_fnynn_map.py --only t_grass,t_water` regenerates a subset.
- **Fnynn animation generator** — `python tools/make_fnynn_anim.py` packs the same character
  and monster rigs into `.vpa` frame strips (attack / cast / hurt / walk) consumed by the
  game's `src/anim.h` loader
- **`.vpe` integration skill** — `/vpe-game-assets` (`scripts/vpe_tool.py`) decodes, atlases,
  builds uniform tilesets and embeds assets for Godot / Pygame / HTML canvas / Unity / C-MRE projects
- Light & Dark enterprise themes via **QSS** (`style/dark.qss`, `style/light.qss`)
- Drop-shadow panels, fade-in window, tool rail with active glow

## Requirements

- Python 3.10+
- PySide6 6.6+

```bash
pip install -r requirements.txt
python main.py
```

Or double-click **`run.bat`** (checks Python/pip, installs deps, creates folders, launches).

## Folders (EXE + source)

| Purpose | Location |
|---------|----------|
| Projects (`.vpe`) | `%USERPROFILE%\Documents\VPE Pixel` |
| Exports (BMP/PNG) | `%USERPROFILE%\Documents\VPE Pixel\exports` |
| Settings / autosave | `%APPDATA%\VXP Pixel Editor` |

## Build EXE → `output/`

```bat
build_all.bat
```

Produces two single files:

```
output/
├── onefile/VXP Pixel Editor.exe        ~46 MB, no Python needed
└── installer/Setup VXP Pixel Editor.exe  ~92 MB, 5-page wizard
```

`Setup VXP Pixel Editor.exe` checks the environment (repairing missing
libraries automatically), copies the app to `%LOCALAPPDATA%\Programs\VXP Pixel
Editor`, adds Desktop / Start Menu shortcuts and an Add/Remove Programs entry,
and ships `Uninstall VXP Pixel Editor.exe` next to the app.
`build_exe.bat` still works if you want the unpacked one-folder tree instead:

```
output/dist/VXP Pixel Editor/VXP Pixel Editor.exe
```

The EXE is windowed (no console), embeds `style/*.qss`, and on first launch creates
`APPDATA\VXP Pixel Editor` + `Documents\VPE Pixel`. See `docs/BUILD.md` for the
installer flags (`--quiet`, `--uninstall`, `--target`, `--no-shortcuts`).

## VPE565 format

| Offset | Size | Field |
|-------:|-----:|-------|
| 0 | 6 | Magic `VPE565` |
| 6 | 2 | Version `u16` = 1 |
| 8 | 2 | Width `u16` |
| 10 | 2 | Height `u16` |
| 12 | 4 | Payload size `u32` (= w × h × 2) |
| 16 | N | RGB565 pixels, row-major, little-endian |

Max dimension: 640×640 (same as the Lua editor).

There is **no alpha channel**. White (`0xFFFF`) is only the editor's
"no background" convention — converting it to real transparency is an explicit
choice in the export step.

## Use assets in a game or app

The repo ships a project skill, `/vpe-game-assets`, whose CLI needs nothing but
Python 3.10+ (no PySide6, no Pillow) and can be copied into any consuming project:

```bash
TOOL=.qoder/skills/vpe-game-assets/scripts/vpe_tool.py

python $TOOL inspect   "Documents/VPE Pixel/sprite"/*.vpe      # confirm sizes first
python $TOOL png       hud_heart.vpe --out build/ --scale 4 --transparent-white
python $TOOL atlas     --dir "Documents/VPE Pixel/sprite" --out assets/sprites.png --json assets/sprites.json --transparent-white
python $TOOL tileset   --dir "Documents/VPE Pixel/tile" --out assets/tiles.png --json assets/tiles.json --size 16
python $TOOL batch-export --dir "Documents/VPE Pixel" --out build/assets --scale 2 --transparent-white
python $TOOL header    hero_idle.vpe --lang c --out hero_idle.h   # embedded, loader-free
```

`atlas`/`tileset` metadata is JSON: frame `textureRect`s for spritesheets, and
`tileWidth/columns/rows/tiles[]` (Tiled-shaped) for tilesets.
Loader recipes for Godot 4, Pygame, HTML canvas, Unity C# and C/MRE are in
`.qoder/skills/vpe-game-assets/references/engine-loaders.md`; the workflow itself
is in `.qoder/skills/vpe-game-assets/SKILL.md`. The reusable agent prompt lives
in `PROMPT.md` §8.

## Shortcuts

| Key | Action |
|-----|--------|
| `B` / `E` / `G` / `L` / `U` / `R` / `I` | Pencil / Eraser / Fill / Line / Rect / Filled / Pick |
| `1`–`5` or `[` `]` | Brush size |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / Redo |
| `Ctrl+0` / `Ctrl+=` / `Ctrl+-` | Fit / Zoom in / Zoom out |
| `Ctrl+G` / `Ctrl+T` | Toggle grid / theme |
| `Ctrl+E` / `Ctrl+Shift+G` | Open / toggle asset collection gallery |
| Scroll wheel | Zoom |
| Right-drag / Middle-drag | Pan |
| Double-click canvas | Fit |

## Project layout

```
Pixel_Editor/
├── main.py                 # entry
├── requirements.txt
├── style/
│   ├── dark.qss            # dark theme tokens
│   └── light.qss           # light theme tokens
├── vpx_editor/
│   ├── vpe.py              # VPE565 + BMP/PNG codec
│   ├── gallery.py          # asset collection (titleset/sprite/texture/tile)
│   ├── document.py         # canvas buffer + undo history
│   ├── canvas.py           # interactive zoomable canvas
│   ├── main_window.py      # enterprise chrome
│   ├── widgets.py          # shadow cards, palette, chips
│   ├── theme.py            # design tokens + QSS loader
│   ├── palette.py          # classic 16-color palette
│   └── dialogs.py          # New canvas / New asset / About
├── tools/
│   ├── make_samples.py     # procedural .vpe sample library (285 assets)
│   ├── make_fnynn_map.py   # Fnynn farm-RPG tiles + sprites (92 assets)
│   ├── make_fnynn_anim.py  # Fnynn .vpa animation strips
│   └── make_vqeaf_icons.py # VQEAF OS system icons (24 assets)
├── docs/
│   └── ASSET_TAXONOMY.md   # asset families, folder mapping, VPE565 limits
├── .qoder/skills/vpe-game-assets/   # /vpe-game-assets — consume .vpe in games/apps
│   ├── SKILL.md
│   ├── scripts/vpe_tool.py
│   └── references/engine-loaders.md
├── PROMPT.md               # product requirements + integration prompt
├── SKILLS.md               # working conventions for humans and agents
└── test_smoke.py           # codec + document + GUI + gallery + pipeline smoke tests
```

## Tests

```bash
python test_smoke.py
```

Verifies VPE565 round-trip (including a real project sample from the LuaS30 tree),
document tools / undo, and offscreen GUI construction.
