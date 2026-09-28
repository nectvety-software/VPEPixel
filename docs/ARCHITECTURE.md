# Architecture

## Overview

```
main.py                     entry: pre-Qt env gate, QApplication, font, theme, ensure_layout()
vpx_editor/
  paths.py                  APPDATA + Documents\VPE Pixel + frozen detection
  vpe.py                    VPE565 codec + BMP/PNG import/export
  vpea.py                   VPEA01 animation container + PNG strip export
  document.py               pixel buffers (frames) + stroke transactions + undo/redo
  canvas.py                 zoomable interactive canvas widget
  timeline.py               frame strip, playback timer, onion skin + frame tools
  main_window.py            chrome: menus, tool rail, side panels, status
  gallery.py                asset collection browser + VPE thumbnails
  widgets.py                ShadowCard, PaletteGrid, SizeSelector, chips
  theme.py                  design tokens + QSS token fill + palette apply
  palette.py                classic 16 RGB565 colors (from Lua editor)
  dialogs.py                New Canvas, About, custom color
  icons.py                  Segoe MDL2 glyph icons + text fallback
  envcheck.py               stdlib-only environment checks + console repair (no Qt)
  bootstrap.py              Qt environment dialog + repair worker over envcheck
style/
  dark.qss / light.qss      QSS skins (@token placeholders)
installer/
  setup_wizard.py           5-page install wizard + uninstaller (same binary)
  setup.spec                PyInstaller build of the wizard, embeds the app EXE
  app.ico                   icon for the app and the setup file
tools/
  make_app_icon.py          renders installer/app.ico
  make_ui_buttons.py        procedural button asset family
  make_vqeaf_screens.py     procedural VQEAF_OS screen mockups
  make_knight_anim.py       procedural .vpea animation set (sword + shield knight)
  play_animations.py        drives real timeline playback, writes preview GIFs
build_exe.spec              PyInstaller one-folder build
build_onefile.spec          PyInstaller one-file build (the installer payload)
run.bat / build_exe.bat / build_all.bat
test_smoke.py               codec + vpea + document + GUI + timeline + envcheck + installer tests
```

Startup order matters: `main.py` imports `envcheck` (stdlib only) before any Qt
module, so a missing PySide6 is reported in the console; `bootstrap` is only
imported once Qt is proven importable.

## Data flow

```
User input (mouse/keyboard)
        │
        ▼
CanvasView  ──paint_brush / flood_fill / line / rect──►  Document
        │                                                   │
        │                                          undo / redo stacks
        │                                                   │
        ▼                                                   ▼
   QPainter view ◄── pixmap rebuild ◄── RGB565 pixels
        │
        ▼
 save .vpe (vpe.encode_vpe)  /  export BMP|PNG
```

## Document model

- Pixels are **RGB565** integers (`List[int]`, row-major).
- A document owns `frames: List[List[int]]` plus `frame`, `delay_ms`, `loop`.
  `doc.pixels` **aliases** `frames[frame]`, so every existing paint, fill and
  export path works unchanged on the current frame.
- `begin_stroke` / `stroke_set` / `end_stroke` collect `(x, y, old, new)` once
  per stroke → one undo step (matches the Lua editor’s transaction model).
- Each `HistoryEntry` stamps the frame it belongs to, so undo/redo jump to that
  frame instead of applying the change to whatever is on screen.
- `move_frame` / `delete_frame` reorder by list **identity**, not equality —
  two identical frames must stay distinguishable.
- Fill uses span-based flood fill (no recursion, no visited bitmap —
  recolored runs act as markers).

## Animation

| Piece | Responsibility |
|-------|----------------|
| `vpea.py` | VPEA01 container: 20-byte header + N self-contained VPE565 payloads; `header_of`, `frame_count_of`, `load_frame` read without decoding everything; `save_png_strip` writes a keyed spritesheet |
| `document.py` | frame list, `goto_frame`, `add/duplicate/delete/move_frame`, `from_frames`, `to_vpea_bytes`, `from_vpea_bytes` |
| `timeline.py` | `TimelineBar` (two rows: transport + strip of `FrameChip` thumbnails) and the playback `QTimer`; owns no pixels |
| `canvas.py` | onion skin — `_ghosts` are pre-faded `QPixmap`s of `Document.onion_frames()` neighbours, white keyed out |
| `main_window.py` | `&Animation` menu, `Space` / `,` / `.` keys, `.vpea` open/save dispatch, frame info chip |

Rules that keep the two formats honest:

- `.vpe` is single-frame and byte-compatible with LuaS30 — never widened.
- Saving an animated document to a `.vpe` path is redirected to Save As.
- The gallery reads frame 0 of a `.vpea` for its thumbnail and shows the frame
  count on the card (`SPRITE · 5F`).
- Playback pauses onion skin and restores the previous state on stop, because
  ghosts make an animation preview unreadable.

## Canvas view

| Feature | Notes |
|---------|-------|
| Zoom | 1×–64×, scroll wheel, `Ctrl+=` / `Ctrl+-` |
| Pan | Middle-drag or right-drag |
| Fit | Double-click or `Ctrl+0` |
| Grid | Pixel lines when zoom ≥ 4 (`Grid` toggle) |
| BG | Checker bed under sprite (`BG` toggle) |
| No BG | White `0xFFFF` → transparent (`No BG` toggle) |
| Shadow | Soft drop shadow under the art board |

## Theme

1. Tokens in `theme.py` (`DARK` / `LIGHT` dicts).
2. QSS files use `@token` placeholders.
3. `_fill_tokens` replaces **longest keys first** so `@surface2` is not
   clobbered by `@surface`.
4. `Theme.apply_to_app()` sets QSS **and** `QPalette` (Fusion fallback).

Never set `font-family` in QSS — a multi-family list breaks glyph resolution
in Qt. Fonts are set via `QApplication.setFont()` in `main.py`.

## Icons

`icons.py` draws the chrome from the **Segoe MDL2 Assets** icon font instead of
letter abbreviations. Glyphs go through a `QIconEngine`, so they are painted at
the widget's icon size and pick up the live theme colour on every paint — a
Light/Dark switch recolours them with no re-wiring (`iconId()` changes with the
theme so Qt drops its pixmap cache).

- `GLYPHS` maps a role name to `(codepoint, abbreviation)`. Codepoints are
  private-use-area values; pick new ones by rendering a sheet and looking, not
  from documentation.
- `available()` is checked at runtime: the family is missing on the offscreen
  platform plugin and on non-Windows desktops. When it is missing, `set_icon()`
  installs a null icon and the abbreviation becomes the button text, so no
  control ever renders empty.
- Hover titles are mandatory: `test_hover_titles()` in `test_smoke.py` fails if
  any button, line edit, combo, spin box or menu action has an empty `toolTip()`.

## Paths (frozen EXE vs source)

| Role | Location |
|------|----------|
| Projects `.vpe` | `Documents\VPE Pixel` |
| Exports | `Documents\VPE Pixel\exports` |
| Settings / autosave | `%APPDATA%\VXP Pixel Editor` |
| QSS in EXE | `_internal/style/*.qss` (PyInstaller datas) |

`paths.is_frozen()` is true under PyInstaller; `theme._style_dir()` searches
`_MEIPASS`, `_internal`, then the source tree.

## UI layout

```
┌──────────────────────────────────────────────────────────┐
│ Menu  File Edit Animation View Tools Help                 │
├────┬─────────────────────────────────────┬───────────────┤
│Tool│  top bar: title · zoom · fit        │ Color         │
│rail│  ┌─────────────────────────────┐    │  palette 16   │
│ 7  │  │     pixel canvas + grid     │    │ Brush  1–5    │
│btns│  │     shadow / checker / BG   │    │ View BG/NoBG  │
│    │  └─────────────────────────────┘    │     /Grid     │
│Thm │  timeline: transport · fps · onion  │ Document info │
│    │  frame strip — one chip per frame   │ Export buttons│
├────┴─────────────────────────────────────┤               │
│ Status: x y · tool · zoom · color · path └───────────────┘
└──────────────────────────────────────────────────────────┘
```

## Testing

```bat
python test_smoke.py
```

1. VPE encode/decode round-trip (byte-identical vs Lua sample).
2. Document tools + undo/redo.
3. VPEA container: layout, delay clamps, per-frame slicing, strip export, rejects.
4. Offscreen GUI construction.
5. Animation UI: frame stepping, per-frame paint isolation, onion ghosts,
   duplicate/move/delete, real-timer playback, `.vpea` save + reopen.
6. Hover titles on every interactive control.
7. Gallery classification (including `.vpea`) + thumbnails + panel.
8. `vpe_tool` CLI, button family, knight animation sample, icon table.
9. Environment checks + installer wiring.
