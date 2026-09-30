---
name: vpe-game-assets
description: Integrate VXP Pixel Editor .vpe (VPE565 / RGB565) and .vpea (VPEA01 animation) assets into a game or app pipeline. Use when converting, packing or loading sprites, sprite animation scenes, titlesets, tilesets or textures from a `Documents\VPE Pixel` folder or any `.vpe` / `.vpea` files - decode to PNG, build spritesheet atlases with JSON metadata, emit uniform tileset sheets, generate embedded C/Python/JS/JSON pixel headers for engine-less targets, or write engine loaders for Godot, Pygame, HTML canvas, Unity and LuaS30/MRE.
---

# VPE game asset integration

## Overview

`.vpe` files are VPE565: raw RGB565 bitmaps with no alpha and no engine-specific
encoding; `.vpea` files are VPEA01 - the same bitmaps, N frames of one size in
one file. This skill turns them into whatever the target engine needs - PNG
spritesheets, tileset sheets, or embedded pixel arrays - with a stdlib-only CLI
that runs in any project (no PySide6, no Pillow). Animations expand to one
atlas entry per frame.

## Format facts that drive every decision

| Fact | Consequence |
|------|-------------|
| Header: `VPE565` + `u16 ver=1` + `u16 w` + `u16 h` + `u32 payload`, then `w*h` little-endian `u16` | 16 bytes + `w*h*2` exactly; any other size means corruption, not a variant |
| RGB565, 5/6/5 bits, no alpha channel | "Transparent" is an *editor convention*: white (`0xFFFF`). Never assume it in the engine - opt in with `--transparent-white` |
| Max 640x640, one image per file | A sprite *animation* is either several files or one `.vpea` (below) |
| `.vpea` = VPEA01: 20-byte header (`VPEA01` + `u16 ver=1` + `u16 w` + `u16 h` + `u16 frameCount` + `u16 delayMs` + `u8 loop` + 3 zero bytes) then `frameCount` complete VPE565 blobs of `16+w*h*2` bytes | One file holds the whole scene; every frame is the same size, so an atlas can pack them as a row. `tools/play_animations.py` in the editor repo is the reference player |
| Channel restore is `(v>>11)*8, ((v>>5)&63)*4, (v&31)*8` | Pure `*8/*4` expansion loses low bits; use it consistently in loader and shader alike |
| Row-major, top row first, no padding | Line stride is `w*2` bytes, never 4-byte aligned - do not feed directly to APIs requiring pitch alignment |
| `rgb(252..255, 252..255, 252..255)` all collapse to `0xFFFF` | When *authoring* solid tiles/textures, keep the brightest highlight at `rgb(246, 252, 255)` or below, or the editor's white-key will punch holes in it |

## Asset folder layout

The editor writes into `Documents\VPE Pixel\<category>\` (categories:
`titleset`, `sprite`, `texture`, `tile`; plus legacy project subfolders). A
category folder is the natural atlas boundary - `batch-export` groups by it.

Categories group further by genre, and the grouping is part of the shipped
sample library, so grep for it rather than assuming a flat folder:

```
sprite/characters/player/       # td_hero_*.vpe stills + hero_<dir>_<action>.vpea scenes
sprite/enemies/boss/            # dragon_ / golem_ / slime_ / wizard_ / scorpion_<action>.vpea, 48x48
sprite/enemies/  sprite/items/icons/  sprite/ui/hud/  sprite/vfx/particles/
sprite/effect/                # reusable skill FX as .vpea, one scene per file
tile/topdown/{terrain,roads,architecture,interior,flora}/   tile/side/{platform,hazard}/
texture/background/parallax/   texture/ui/
```

Name prefixes carry the same information: `td_` top-down, `sp_` side-scroller,
`bg_` parallax layer, `ic_` item icon, `hud_` UI, `fx_` particle or effect. Every
`atlas`/`tileset` command accepts `--dir` at any depth, so pack one family at a
time (`--dir .../sprite/characters/player`) instead of filtering a huge atlas.
`atlas` expands a `.vpea` into one record per frame and keeps `source`,
`frame`, `frameCount`, `delayMs` and `loop` in the JSON, so the stills and the
animated hero can share one sheet and still be told apart by the loader.

## Workflow

Run the bundled tool from any working directory:

```bash
python <skill-dir>/scripts/vpe_tool.py <command> ...
```

All commands print one line per file (`OK ...` / `ERROR Type: message`) and
exit non-zero only when nothing usable was produced. Suppress tracebacks; parse
stdout.

### 1. Verify before building anything

```bash
python scripts/vpe_tool.py inspect "Documents/VPE Pixel/sprite"/*.vpe *.vpea
```

Prints `name  WxH  images=N  bytes`, plus `N-frame animation @delay ms loop=…`
for `.vpea`. Use this first - a wrong assumption about size is the most common
cause of a broken atlas.

### 2. One-shot PNGs (quick look, engine-native import folders)

```bash
python scripts/vpe_tool.py png hud_heart.vpe --out build/ --scale 4 --transparent-white
```

`--scale N` is nearest-neighbour, so pixel art stays crisp. `--transparent-white`
turns `0xFFFF` into alpha 0; omit it for backgrounds and textures where white is
a real colour.

### 3. Sprite atlas + metadata (the normal runtime path)

```bash
python scripts/vpe_tool.py atlas --dir "Documents/VPE Pixel/sprite" \
    --out assets/sprites.png --json assets/sprites.json --scale 1 --transparent-white
```

Packs with a shelf algorithm and a 1px transparent gutter between frames (the
sheet has no outer margin - frame 0 sits at `0,0`), width derived from total
area. Output JSON:

```json
{ "image": "sprites.png", "width": 223, "height": 262, "scale": 1,
  "transparentWhite": true, "format": "VPE565/RGB565 -> RGBA8",
  "frames": [ { "filename": "hero_idle.vpe",
                "textureRect": { "x": 0, "y": 0, "w": 16, "h": 16 } },
              { "filename": "knight_attack_01", "source": "knight_attack.vpea",
                "frame": 1, "frameCount": 8, "delayMs": 90, "loop": false,
                "textureRect": { "x": 33, "y": 0, "w": 32, "h": 32 } } ] }
```

`filename` keeps the `.vpe` extension for stills, so key the runtime lookup on
`Path(f["filename"]).stem`. Frames arriving from a `.vpea` are the exception:
they are named `<stem>_NN` and carry `source` / `frame` / `frameCount` /
`delayMs` / `loop` - group by `source`, sort by `frame`, and drive playback from
`delayMs` (that is how the editor's own timeline does it). Frames arrive sorted
by descending height - do not assume alphabetical order matches the array index.

### 4. Tileset sheet (uniform tiles only)

```bash
python scripts/vpe_tool.py tileset --dir "Documents/VPE Pixel/tile" \
    --out assets/tiles.png --json assets/tiles.json --size 16
```

Refuses mixed tile sizes (`ERROR tileset needs uniform tile size`); use `--size`
to filter or split into separate sheets. JSON carries `tileWidth/tileHeight/
columns/rows/tileCount/tiles[].index`, deliberately shaped like a Tiled/LDTile
map so a map editor can consume it without a translation layer.

### 5. Batch every category at once

```bash
python scripts/vpe_tool.py batch-export --dir "Documents/VPE Pixel" \
    --out build/assets --scale 2 --transparent-white
```

One atlas + JSON per group. Group name comes from the category folder, else the
first path component under `--dir`, lowercased and sanitised
(`puzzlefield_atlas.png`, `sprite_atlas.png`, ...).

### 6. Embedded headers (no image loader at all)

```bash
python scripts/vpe_tool.py header hero_idle.vpe --lang c --out hero_idle.h
python scripts/vpe_tool.py header coin_0.vpe  --lang js --out coins.js
```

`--lang c` emits `static const unsigned short NAME[]` plus `NAME_W/_H/_LEN`
macros - ideal for MRE/LuaS30/STM32/Android-NDK targets where the asset must be
compiled in. `--lang py` gives `NAME/WIDTH/HEIGHT/PIXELS`, `--lang js` an
`export const NAME = { name, width, height, pixels: [...] }`, `--lang json`
`{ "name", "width", "height", "format": "rgb565_le", "pixels": [...] }`. The
pixel array stays RGB565; decode at load time with the bit math above.

## Engine loaders

Full copy-paste recipes for Godot 4, Pygame, HTML canvas/JS, Unity C# and raw
C/MRE are in `references/engine-loaders.md`. Read only the section you need.

Minimum contract for any loader:

- **Godot**: import PNGs with *Lossless*, filter **Off** (Linear blurs pixel art), then `AtlasTexture` per frame from `textureRect`.
- **Pygame**: `pygame.image.load(path).convert_alpha()`, then `pygame.transform.scale(..., Smoothscale=False)`; blit sub-rects from the JSON.
- **HTML canvas**: `imageSmoothingEnabled = false`; `drawImage(atlas, sx, sy, sw, sh, dx, dy, sw, sh)`.
- **Unity**: sprite mode *Multiple* using the JSON rects, Point filter, Compression **None**, no mipmaps.
- **C / MRE**: use `header --lang c` and blit `u16` values directly - the target framebuffer is already RGB565, so zero decoding cost.

## Conventions

- Never hand-roll the VPE header; import `vpx_editor.vpe` (`encode_vpe`,
  `decode_vpe`, `rgb_to_565`, `c565_to_rgb`) inside this repo, and copy
  `decode_vpe` from `scripts/vpe_tool.py` in external projects.
- Validate magic, version, dimensions (1..640) and payload length on load. A
  size mismatch is a hard error, not a warning - silently truncating produces
  shifted rows that look like a palette bug.
- Keep atlases at the project's `--scale` (1 for native pixel art, integer
  >1 only if the engine scales per-sprite). Fractional scale makes seams.
- After regenerating an atlas, update the engine's import metadata too - stale
  `.import`/`.meta` files are the usual reason a rebuilt sheet "did not change".
- Generated artefacts go in the consuming project (`assets/`, `build/`), never
  back into `Documents\VPE Pixel`, which is the editor's source tree.

## Verification checklist

Before reporting the pipeline as working:

1. `inspect` shows every expected file and dimension; no `ERROR` lines.
2. Atlas PNG opens, dimensions match the reported `WxH`, and - on a source asset
   that actually contains `0xFFFF` - `--transparent-white` yields a non-zero
   transparent pixel count while the same run without the flag yields zero.
   (An artwork with no white legitimately reports 0 either way; count the white
   pixels in the `.vpe` payload before treating this as a failure.)
3. Frame count in the JSON equals the file count (minus any printed `ERROR`s).
4. Composite the atlas over a dark background and view it (a screenshot or
   `Read` of the PNG) - a packer bug is visible before it is measurable.
5. Round-trip proof: re-encode one frame's pixels back to VPE565 and compare
   bytes with the source `.vpe`; they must be identical.

## Resources

- `scripts/vpe_tool.py` - the CLI described above. Stdlib only
  (`argparse`, `struct`, `zlib`, `json`, `math`, `pathlib`); its PNG writer is
  implemented inline so no imaging dependency is required.
- `references/engine-loaders.md` - per-engine loader snippets and pitfall notes.
