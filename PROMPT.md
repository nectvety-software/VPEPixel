# PROMPT.md — VXP Pixel Editor (Python / PySide6)

Product prompt and requirements used to design and implement this app.
Keep this file as the source of truth for scope; update it when the product changes.

---

## 1. Source project

Reference implementation (LuaS30 / Nokia S30+ / MRE):

```
C:\Users\doxuanhop\Documents\LuaS30 Projects\VXP_Pixel_Editor
```

Key artifacts from the reference:

- `src/40_rgb565.lua` — RGB565 buffer + `encode_vpe565` / `decode_vpe565`
- `src/70_editor.lua` — tools, palette (16 colors), undo
- `projects/JustKeepSwimming/*.vpe` — real sprites
- Docs under `docs/` (IMPORT_VPE_QA, DARK_UI, PHASE2E pixel tools)

## 2. Original request (user)

> dự án VXP_Pixel_Editor → code phần mềm vẽ dùng Python, PySide6 và xuất ra file `.vpe`.
> Chuyên nghiệp, giao diện tối, Enterprise. Đẹp xuất sắc.
> Hiệu ứng đổ bóng, animation, Light/Dark Mode mượt mà.
> Tùy biến giao diện bằng QSS (giống CSS), file `style.qss`.
>
> thêm `run.bat` kiểm tra thư viện môi trường và cập nhật và chạy
>
> xuất ra thư mục `output` nếu cài exe thì có `APPDATA` và lưu vào thư mục `Documents\VPE Pixel`
>
> thêm bật tắt nền và không nền có kẻ ô
>
> tạo thư mục `docs` rồi viết tài liệu và `PROMPT.md`, `SKILLS.md`

### Translation of intent

1. Professional pixel drawing app in **Python + PySide6**
2. Save/export native **`.vpe`** (VPE565)
3. Dark, enterprise-grade UI (shadows, animations, Light/Dark, QSS)
4. `run.bat` — env check + dependency update + launch
5. Build EXE into `output/`; app data → **APPDATA**; projects → **Documents\VPE Pixel**
6. Toggles: **background**, **no-background**, **grid**
7. `docs/` + `PROMPT.md` + `SKILLS.md`

### Follow-up requests (2026-09)

| User text (verbatim) | Intent |
|----------------------|--------|
| “vẽ bộ sưu tập cho game như titleset, sprite, texture” | Asset **collection / gallery** view, categorised as titleset · sprite · texture (tile added) |
| “các mẫu ảnh ở vị trí thư mục nào” | Gallery must show assets wherever they live → recursive scan of `Documents\VPE Pixel` |
| “vẽ nhiều mẫu tài nguyên hơn không chỉ riêng puzzle field” | Ship a **sample asset library** beyond the one PuzzleField set |
| “viết prompt và skills tích hợp .vpe vào khi phát triển game hay ứng dụng” | **Prompt + skill** for consuming `.vpe` in a game/app build pipeline |

## 3. Functional requirements

### Canvas & tools
- RGB565 pixel canvas, max 640×640
- Tools: Pencil, Eraser, Fill, Line, Rectangle, Filled Rectangle, Eyedropper
- Brush size 1–5
- Undo / redo (stroke = one history entry)
- Zoom, pan, fit, pixel grid
- Background checker, no-background (white → transparent preview), grid toggles

### Color
- Classic 16-color palette from the Lua editor (exact RGB565 values)
- Custom color picker
- Hex display (`#RRGGBB` + `F800`)

### Files
| Action | Format |
|--------|--------|
| Save / Open | `.vpe` VPE565 |
| Export | BMP 24-bit, PNG |
| Import | PNG / JPG / BMP → RGB565 |

### UI / aesthetic
- Enterprise dark default + light mode
- QSS theming (`style/dark.qss`, `style/light.qss`)
- Drop shadows on cards, fade-in window, tool rail glow
- Status bar: coords, tool, zoom, color, path

### Packaging
- `run.bat` for source launch
- `build_exe.bat` → `output/dist/VXP Pixel Editor/VXP Pixel Editor.exe`
- `%APPDATA%\VXP Pixel Editor` for settings
- `Documents\VPE Pixel` (+ `exports`) for user files

### Asset collection (gallery)
- Toggle with `Ctrl+E` (File / View menus too); editor and gallery are two pages
  of one `QStackedWidget`, so unsaved canvas state survives the switch
- Categories: `all`, `titleset`, `sprite`, `texture`, `tile` →
  one folder each under `Documents\VPE Pixel`
- Recursive scan (depth 4: `root → category → group → sub-group`, e.g.
  `sprite/characters/player/`) of the project folder, skipping `exports` and dot-dirs
- Kind inference: nearest known category ancestor wins, else dimensions
  (≥128×128 → titleset, longest edge ≥ 4× shortest → texture, ≤24×24 → tile, else sprite)
- Thumbnails honour the white-is-transparent rule for `sprite`/`tile`
- Per-card actions: open in editor, duplicate, move to category, rename,
  reveal in Explorer, delete (**Recycle Bin**, not `rm`)
- New blank asset + import image, search box, live count
- View and last folder persist in `settings.ini` (keys `view`, `last_dir`, `theme`)

### Sample asset library
- Two deterministic, stdlib-only generators write `.vpe` straight into the
  category folders:
  - `python tools/make_samples.py [--only sprite]` — **285** game-art assets
  - `python tools/make_vqeaf_icons.py` — **24** VQEAF OS system icons
    (`tile/<name>_24.vpe` + `sprite/<name>_36.vpe`, keyed background by design)
- `make_samples.py` ships 9 titlesets, 172 sprites/FX frames, 19 textures, 85 tiles:
  - **136** pre-taxonomy assets (82 sprites/FX, 32 tiles, 13 textures, 9 titlesets),
    of which the arctic "Snow Base Defense" set is 69 assets: 3 portrait screens,
    49 sprites (37 figures/props + 12 HUD badges), 13 tiles (6 snow kinds + 2 sea +
    5 cliff edges), 4 texture sheets
  - **149** taxonomy assets laid out in the sub-folder tree of
    [`docs/ASSET_TAXONOMY.md`](docs/ASSET_TAXONOMY.md): top-down terrain / roads /
    architecture / interior / flora (42), side-scroller platforms + hazards (11),
    4-direction × 12-action player (49), enemies (14), item icons (10), HUD (5),
    particles (12), parallax layers (5), dialogue frame (1)
- Must stay reproducible: fixed seeds, no network, no Pillow
- Solid art (tiles, textures, screens) must never emit `0xFFFF`: the gallery keys
  pure white as transparency, so a white speckle punches a hole in a tile. Use
  `AR_LIT = rgb(246, 252, 255)` for the brightest snow highlight and clamp
  `tile_base` highlights at 248. `0xFFFF` is only allowed where the art is
  deliberately transparent (`ladder`, `bridge`, `ar_edge_tl/tr` corners, the
  saw blade and spike hazards, and the VQEAF system icons, whose whole point is
  a keyed background)

### Game / app integration pipeline
- `.qoder/skills/vpe-game-assets/` — skill + `scripts/vpe_tool.py` (stdlib only,
  no PySide6/Pillow) with `inspect` · `png` · `atlas` · `tileset` · `header`
  (c/py/js/json) · `batch-export`
- Loader recipes for Godot 4, Pygame, HTML canvas, Unity, C/MRE in
  `references/engine-loaders.md`
- Reusable prompt in §8 below

## 4. Non-goals

- Multi-layer compositing / animation timeline (Lua GIF scenes out of scope)
- Network / cloud
- CMYK or 32-bit RGBA project format (VPE is RGB565 only)
- **3D PBR material maps** (normal / roughness / metallic / AO / height). RGB565
  carries three quantised colour channels and no linear-data workflow, so these
  cannot be represented without visible banding. `texture/` means albedo,
  background and UI-panel art only — see [`docs/ASSET_TAXONOMY.md`](docs/ASSET_TAXONOMY.md) §2

## 5. Acceptance checks

- [x] Open Lua `hud_heart.vpe`, re-save → byte-identical
- [x] Edit one pixel → only that pixel changes
- [x] `python test_smoke.py` passes
- [x] EXE creates `APPDATA\VXP Pixel Editor` and `Documents\VPE Pixel`
- [x] BG / No BG / Grid toggles work
- [x] Light/Dark QSS apply without glyph breakage
- [x] Gallery lists the recursive `PuzzleField` set (18 assets) plus all categories
- [x] `make_samples.py` regenerates 285 assets byte-stable on a clean folder
- [x] `vpe_tool.py atlas --dir …/sprite/characters/player` → `112x153, frames=49`, transparent pixels present
- [x] `vpe_tool.py tileset --dir …/tile/topdown/terrain --size 16` → `48x48, 3x3, tiles=9`; mixed sizes rejected
- [x] `vpe_tool.py batch-export` groups by category (puzzlefield 18 · sprite 184 · texture 19 · tile 97 · titleset 9 = 327 assets — 285 from `make_samples.py`, 24 from `make_vqeaf_icons.py`, plus the 18 `PuzzleField` screens)
- [x] No solid tile/texture contains `0xFFFF` (`ar_snow_*`, `ar_edge_top/left/right`, `snow` all report `white=0`)
- [x] `header --lang c` array equals the source payload; decode→re-encode is byte-identical

## 6. Constraints & lessons

1. Qt QSS `font-family` lists break fonts → set font in code only.
2. Token replace must be **longest-first** (`@surface2` vs `@surface`).
3. VPE magic is exactly `VPE565\x01\x00` (version in the 8-byte header).
4. Even brush sizes: cursor = top-left (matches Lua). Odd: cursor = center.
5. RGB565 has no alpha — “No BG” is display-only for white, so transparency at
   runtime is always an **opt-in** (`--transparent-white`), never a default.
6. A non-recursive asset scan hid the user's existing `PuzzleField` folder —
   the collection must walk subfolders, and any “I can't see X” report is a
   discoverability question, not necessarily a code bug.
7. `QImage.scanLine()` cannot be written back; build one contiguous
   `bytearray(w*h*4)` and construct the `QImage` from it.
8. Shelf packing from *summed widths* gave a 25×518 strip; derive width from
   total area plus the widest item.
9. Console output with non-ASCII dashes mangles error text on Windows (`bad
   magic ?`); keep tool stdout ASCII so agents can parse it.
10. Verify with repo-local paths, not `/tmp` — Git Bash and native Python resolve
    it differently and a validation loop can silently check nothing.
11. `lighten()` of a near-white 565 colour lands exactly on `0xFFFF`, which the
    gallery then keys out — "brightest usable snow" is `rgb(246, 252, 255)`, and
    green must stay ≤ 251 to avoid rounding up to the white code.
12. `hash()` is salted per process, so it silently breaks generator
    determinism — derive seeds from a stable char-weighted sum instead.

## 7. Current product name

| Item | Value |
|------|-------|
| App name | VXP Pixel Editor |
| Package | `vpx_editor` |
| Project folder | `Documents\VPE Pixel` |
| Settings folder | `APPDATA\VXP Pixel Editor` |
| EXE | `output/dist/VXP Pixel Editor/VXP Pixel Editor.exe` |
| Gallery skill | `.qoder/skills/vpe-game-assets/` |

## 8. Prompt — integrate `.vpe` assets into a game or app

Copy this into an agent working in the **consuming** project (not this repo).
It is the deliverable requested by “viết prompt và skills tích hợp .vpe vào khi
phát triển game hay ứng dụng”.

```
Task: wire VXP Pixel Editor assets into this project's asset pipeline.

Source of truth
- Assets are VPE565 `.vpe` files under `Documents\VPE Pixel\<category>\`,
  categories: titleset | sprite | texture | tile.
- Layout: `VPE565` + u16 version(=1) + u16 width + u16 height + u32 payload,
  then width*height little-endian RGB565 values. Header is 16 bytes, file size
  is exactly 16 + w*h*2. Max 640x640.
- There is NO alpha channel. White (0xFFFF) is the editor's transparency
  convention and must be converted to alpha only for sprites/tiles, never for
  textures or title screens.

Tooling — use the bundled stdlib CLI, do not write a new decoder
  python <repo>/.qoder/skills/vpe-game-assets/scripts/vpe_tool.py <cmd>
    inspect      FILE...                      verify dims before anything else
    png          FILE... --out DIR --scale N [--transparent-white]
    atlas        --dir DIR --out A.png --json A.json [--transparent-white]
    tileset      --dir DIR --out T.png --json T.json --size 16 [--cols N]
    header       FILE --lang c|py|js|json [--name IDENT] --out FILE
    batch-export --dir "Documents\VPE Pixel" --out DIR --scale N --transparent-white
  It needs nothing beyond Python 3.10. Every command prints one line per file
  and `ERROR <type>: <msg>` on failure.

Steps
1. `inspect` the target folder; record exact file count and dimensions.
2. Pick the delivery shape: atlas + JSON for sprites, uniform tileset for maps,
   `header --lang c` when the runtime has no image loader (MRE/embedded),
   `png --scale 4` for a quick visual check.
3. Generate into THIS project (`assets/` or `build/`), never back into
   `Documents\VPE Pixel`.
4. Write the loader for this project's engine following
   `.qoder/skills/vpe-game-assets/references/engine-loaders.md` (Godot 4,
   Pygame, HTML canvas, Unity C#, C/MRE). Keyed lookup = frame `filename`
   without the `.vpe` suffix. Keep nearest-neighbour filtering everywhere;
   linear filtering on a packed atlas bleeds neighbouring frames.
5. Integer scale only (1 or 2 or 4). Fractional scale produces seams.

Definition of done — verify by execution, show the numbers
- Atlas reported WxH matches the PNG on disk; frame count == file count minus
  printed ERROR lines.
- With `--transparent-white` the PNG has a non-zero transparent pixel count;
  without it, zero.
- Round-trip: decode a frame and re-encode it to VPE565 — bytes identical to the
  source file.
- Composite the atlas over a dark background and actually look at it; a packing
  or filtering bug is visible before it is measurable.
- In-engine: one sprite drawn at native scale, one tilemap drawn, one animated
  frame sequence cycling. Report the engine version and the exact import
  settings you changed.
```

