# SKILLS.md — Working on VXP Pixel Editor

Conventions for humans and AI agents changing this repository.
Read this before editing code, QSS, or packaging scripts.

---

## Project at a glance

| | |
|--|--|
| Stack | Python 3.10+, PySide6 6.6+ |
| Package | `vpx_editor/` |
| Entry | `main.py` |
| Project format | VPE565 (`.vpe`) |
| Themes | `style/dark.qss`, `style/light.qss` |
| Tests | `python test_smoke.py` |
| Source run | `run.bat` |
| EXE build | `build_exe.bat` → `output/` |

---

## Skill: VPE565 codec

**When:** anything that reads/writes `.vpe` or pixel buffers.

- Layout: `VPE565` + `u16 ver=1` + `u16 w` + `u16 h` + `u32 payload` + RGB565 LE pixels.
- Always validate magic, version, size, payload length (see `docs/VPE_FORMAT.md`).
- Prefer `vpx_editor.vpe.encode_vpe` / `decode_vpe` — do not hand-roll headers.
- Round-trip must be byte-stable; test against
  `...\VXP_Pixel_Editor\projects\JustKeepSwimming\hud_heart.vpe` when available.

```python
from vpx_editor.vpe import encode_vpe, decode_vpe, rgb_to_565, c565_to_rgb
```

---

## Skill: Document & undo

**When:** painting tools, history, fill.

- One user stroke = one `HistoryEntry` (list of `(x, y, old, new)`).
- Use `begin_stroke` / `stroke_set` / `end_stroke`.
- Even brush size: top-left anchor. Odd: centered (keep Lua parity).
- Flood fill is span-based; do not replace with recursive DFS.

---

## Skill: Theming (QSS + tokens)

**When:** UI colors, light/dark, stylesheets.

1. Add colors as tokens in `theme.py` (`DARK` / `LIGHT`).
2. Reference them in QSS as `@token_name`.
3. Replacement is longest-first — keep that if you edit `_fill_tokens`.
4. Never put `font-family` lists in QSS (breaks glyphs). Fonts go in `main.py`.
5. Qt QSS does not support `text-transform`; avoid CSS-only properties.
6. `Theme.apply_to_app(app)` must set both stylesheet and `QPalette`.

**View toggles** (canvas):

| Flag | Meaning |
|------|---------|
| `show_background` | Checker bed under sprite |
| `transparent_white` | Display white as transparent |
| `show_grid` | Pixel grid |

---

## Skill: Paths & packaging

**When:** saving files, settings, building EXE.

| Use | Module API | Location |
|-----|------------|----------|
| Projects | `paths.project_dir()` | `Documents\VPE Pixel` |
| Exports | `paths.export_dir()` | `Documents\VPE Pixel\exports` |
| Settings | `paths.settings_file()` | `%APPDATA%\VXP Pixel Editor\settings.ini` |
| Frozen? | `paths.is_frozen()` | PyInstaller |

- After packaging changes, ensure `build_exe.spec` `datas` still includes `style/*.qss`.
- `theme._style_dir()` must find QSS in source **and** `_internal/style`.

---

## Skill: UI structure

**When:** adding panels, tools, shortcuts.

- Tools live in `TOOLS` in `main_window.py` (key, label, shortcut, description).
- Side panels use `ShadowCard` from `widgets.py`.
- Keep object names used by QSS: `Card`, `SidePanel`, `ToolRail`, `Heading`, `Primary`, `Ghost`.
- File dialogs default to `project_dir()` / `export_dir()`, never bare `~/Documents` only.
- View switching uses `QStackedWidget` (`page 0` = canvas host, `page 1` = gallery).
  Never destroy the canvas page — the document must survive a gallery round trip.
- `keyPressEvent` must early-return on the gallery page except `Ctrl+T` /
  `Ctrl+E` / `Ctrl+G`, or painting shortcuts eat gallery typing in the search box.

---

## Skill: Asset collection (gallery)

**When:** `vpx_editor/gallery.py`, categories, thumbnails, asset CRUD.

- The **filesystem is the collection**: one `.vpe` = one asset. There are no
  layers or frames to enumerate.
- Categories are folders: `Documents\VPE Pixel\{titleset,sprite,texture,tile}`
  via `gallery.category_dir(key)`; `ensure_category_dirs()` is idempotent.
- `scan_assets()` is recursive to `MAX_SCAN_DEPTH = 4` (`root → category → group →
  sub-group`), skips `SKIP_DIRS` (`exports`) and dot-dirs, dedupes by path. A
  non-recursive scan hides real user projects — keep it recursive.
- Kind: `asset_kind(path)` = nearest known category **ancestor folder** first, else
  `kind_from_dims` (≥128×128 titleset · longest edge ≥ 4× shortest → texture ·
  ≤24×24 → tile · else sprite). MainWindow uses the **folder-aware** `asset_kind`,
  not raw dims. Walking parents is what lets `sprite/characters/player/` group
  without a registry — see `docs/ASSET_TAXONOMY.md`.
- Thumbnails: build one contiguous `bytearray(w*h*4)` ARGB32 and pass it to
  `QImage(bytes, w, h, w*4, Format_ARGB32).copy()`. Do **not** use
  `QImage.scanLine()` writes (no-ops). For `sprite`/`tile`, map `0xFFFF → alpha 0`.
- Deletion goes through `recycle()` — `SHFileOperationW` with `FO_DELETE` and
  `FOF_SILENT|FOF_NOCONFIRMATION|FOF_ALLOWUNDO|FOF_NOERRORUI`
  (`0x0004|0x0010|0x0040|0x0400`), `pFrom` double-null-terminated, `fFlags` a
  `WORD` (`c_uint16`). Never `unlink`: gallery deletes must be recoverable.
  Non-Windows returns `False` and the caller reports it instead of deleting.
- `AssetCard` emits `clicked(path)` after a 260 ms single-shot debounce (so a
  double-click doesn't open twice) and `context_requested(path, globalPos)`;
  `menu.exec(globalPos)` — not `exec(event)`.
- `_relayout()` recomputes `cols = max(1, (viewport.width() - 8) // (150 + 12))`
  and places cards by `(i//cols, i%cols)`; `QGridLayout.addWidget` has no
  flat-index overload.
- Card QSS object names: `AssetCard`, `AssetThumb`, `AssetName`, `AssetKind`
  (defined identically in both `style/*.qss` using tokens).
- `GalleryPanel.current_folder()` feeds `_save_as`'s default directory;
  `_write_vpe` re-derives `self._asset_category` from the saved path.

---

## Skill: Sample asset library

**When:** `tools/make_samples.py`, adding demo/benchmark art.

```bat
py -3 tools\make_samples.py            &rem all 285 assets
py -3 tools\make_samples.py --only sprite
```

- Pure stdlib + `vpx_editor.vpe.save_vpe`; **no Pillow**, no network, fixed
  `random.Random(seed)` per asset so output is reproducible.
- Draw against the shared `Img` helper (`rect/frame/circle/ellipse/line/tri/
  vgrad/speckle/stamp/text`) and the built-in 3×5 bitmap `FONT` — do not add a
  font dependency for in-canvas text.
- Genre coverage matters more than count: titleset (9), sprite/FX (172),
  texture (19), tile (85). New assets must be **legible at 1×**; check them by
  packing an atlas and looking at it, not by trusting the draw call.
- The arctic "Snow Base Defense" family (69 assets) shares one look through
  `outline()` (1px navy rim on every non-background pixel) + `shade()` (bottom
  exposed pixel darkened) + `snow_cap()`. Add new figures through `_worker()`,
  not by hand-placing rim pixels.
- Seeds must be stable: `hash()` is salted per process, so derive them with the
  `_stable(key)` char-weighted sum.
- `emit(category, name, img, sub="a/b")` writes into nested group folders that
  mirror `docs/ASSET_TAXONOMY.md` §4. Keep the taxonomy prefixes consistent —
  `td_` top-down tile, `sp_` side-scroller, `bg_` parallax layer, `ic_` item
  icon, `hud_` UI, `fx_` particle — because the atlas JSON names are the API
  downstream games use.
- Highlights on **solid** art must stay below the transparency key: `0xFFFF`
  encodes from any colour with r≥248, g≥252, b≥248, so a plain `+N` lighten
  punches holes. Use `safe_light()` (caps channels at 247) or `AR_LIT`.
- Solid tiles/textures must never contain `0xFFFF` — the gallery keys pure white
  as transparent, so a white speckle renders as a hole. Use `AR_LIT`
  (`rgb(246, 252, 255)`) for the brightest snow; `lighten()` of near-white
  silently reaches `0xFFFF`. Reserve `WHITE` for deliberate cut-outs
  (`ladder`, `bridge`, `ar_edge_tl/tr`).
- Regenerating into a folder with user edits overwrites by name — pick distinct
  names or scope with `--only`.

---

## Skill: Integrating .vpe into a game/app

**When:** consuming `.vpe` from another project, engine loaders, atlases.

- Use the project skill: `.qoder/skills/vpe-game-assets/`
  (`/vpe-game-assets`). Its `scripts/vpe_tool.py` is stdlib-only and portable to
  the consuming repo — copy the file, don't import `vpx_editor` across repos.
- Six commands: `inspect`, `png`, `atlas`, `tileset`, `header`, `batch-export`.
  Always `inspect` first; wrong dimension assumptions cause shifted rows that
  look like palette bugs.
- Transparency stays **opt-in** (`--transparent-white`) — RGB565 has no alpha, so
  defaulting to transparent would eat white artwork (title screens, textures).
- `tileset` rejects mixed tile sizes; filter with `--size`.
- `atlas` frames arrive sorted by **descending height**, not alphabetically, and
  carry a 1px gutter between (no outer margin). Key runtime lookup on
  `filename` minus `.vpe`.
- `header --lang c` is the MRE/LuaS30 path: the phone framebuffer is already
  RGB565, so blit the `u16` values directly with a colour key instead of decoding.
- Engine import settings are part of the deliverable: nearest filtering,
  lossless/no compression, no mipmaps, integer scale only.
- Generated artefacts belong in the consuming project; `Documents\VPE Pixel`
  stays the editor's source tree.


---

## Skill: Testing

Before you claim done:

```bat
py -3 test_smoke.py
```

Must pass:

1. VPE round-trip (incl. Lua sample if present)
2. Document paint + undo/redo + fill
3. GUI constructs offscreen (`QT_QPA_PLATFORM=offscreen` for headless)
4. Gallery: folder-vs-dimension classification, white-keyed thumbnails,
   `GalleryPanel` builds and refreshes
5. `.qoder/skills/vpe-game-assets/scripts/vpe_tool.py`: decode rejects bad
   magic/size/payload, `--transparent-white` behaviour, shelf packing does not
   overlap frames, inline PNG writer emits valid RGBA IHDR

For UI changes, also grab a screenshot when possible (`win.grab()`).
Note: pure offscreen often has **zero fonts** — prefer real `windows` platform for screenshots.
Keep test/tool stdout ASCII — em-dashes render as `?` on the Windows console.

---

## Skill: Claude / agent prompts (reusable)

### Feature work
```
Read SKILLS.md (repo root) and docs/ARCHITECTURE.md first.
Implement <feature> in vpx_editor/. Keep VPE565 compatibility.
Update docs if behavior changes. Run python test_smoke.py.
```

### Bugfix
```
Reproduce with test_smoke.py or a short script.
Root-cause before editing. Do not paper over VPE validation errors.
```

### Theme polish
```
Only change style/*.qss and theme.py tokens. No font-family lists.
Dark and light must both work. Test toggle with Theme.apply_to_app.
```

### Packaging
```
Use build_exe.spec / build_exe.bat. Output under output/ only.
APPDATA for settings, Documents\VPE Pixel for projects.
```

### Gallery / asset collection
```
Read the "Skill: Asset collection (gallery)" section of SKILLS.md.
Changes stay in vpx_editor/gallery.py (+ dialogs.py, main_window.py wiring,
AssetCard rules in both style/*.qss). Deletion must stay Recycle-Bin based.
Scan stays recursive. Verify with a real screenshot on the windows platform.
```

### Consuming .vpe from another project
```
Use the /vpe-game-assets skill (.qoder/skills/vpe-game-assets/).
Run vpe_tool.py inspect before assuming any dimension.
Transparency only via --transparent-white. Nearest filtering, integer scale.
Generate into the consuming repo; never write back into Documents\VPE Pixel.
Prove it: atlas dims, frame count, transparent-pixel count, VPE byte round-trip.
```

---

## File map (quick)

```
main.py
run.bat
build_exe.bat
build_exe.spec
PROMPT.md          ← product requirements
SKILLS.md          ← this file
docs/
  README.md
  ARCHITECTURE.md
  VPE_FORMAT.md
  USER_GUIDE.md
  BUILD.md
style/{dark,light}.qss
vpx_editor/
  paths.py  vpe.py  document.py  canvas.py
  main_window.py  widgets.py  theme.py  palette.py  dialogs.py
  gallery.py                    # asset collection (titleset/sprite/texture/tile)
tools/
  make_samples.py               # deterministic .vpe sample library (285 assets)
  make_vqeaf_icons.py           # VQEAF OS system icons (24 assets, keyed background)
.qoder/skills/vpe-game-assets/  # /vpe-game-assets — consume .vpe from other projects
  SKILL.md
  scripts/vpe_tool.py           # stdlib-only: inspect/png/atlas/tileset/header/batch-export
  references/engine-loaders.md  # Godot 4 / Pygame / HTML canvas / Unity / C-MRE
test_smoke.py
```

---

## Definition of done

- [ ] Feature matches PROMPT.md scope
- [ ] `python test_smoke.py` green (all 5 sections)
- [ ] Dark + light still render
- [ ] `.vpe` open/save still byte-safe
- [ ] Gallery still lists assets after the change (recursive scan intact)
- [ ] `.qoder/skills/vpe-game-assets/` docs still match `vpe_tool.py` behaviour
- [ ] Docs updated if user-visible behavior changed
