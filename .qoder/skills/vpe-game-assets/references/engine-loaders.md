# Engine loaders for VPE565 assets

Each recipe consumes the output of `scripts/vpe_tool.py`
(`atlas`/`tileset`/`header`). Two integration styles exist:

- **Baked**: export PNG + JSON once, load them in the engine. Best for Godot,
  Unity, Pygame, web - the engine gets real texture compression and tooling.
- **Direct**: compile the `.vpe` bytes (or `header --lang c|py|js`) into the
  binary and decode RGB565 at load time. Best for MRE/LuaS30, MCU, or any
  runtime that already works in RGB565.

Decode math used throughout:

```
r = (v >> 11) * 8          g = ((v >> 5) & 63) * 4          b = (v & 31) * 8
```

---

## Godot 4 (GDScript)

Export: `atlas --dir .../sprite --out res://assets/sprites.png --json res://assets/sprites.json --transparent-white`

```gdscript
extends Node2D

var _frames := {}

func _ready() -> void:
    var tex := load("res://assets/sprites.png") as Texture2D
    var meta := JSON.parse_string(FileAccess.get_file_as_string("res://assets/sprites.json"))
    for f in meta["frames"]:
        var name: String = f["filename"].get_basename()   # strips ".vpe"
        var r: Dictionary = f["textureRect"]
        var at := AtlasTexture.new()
        at.atlas = tex
        at.region = Rect2(r["x"], r["y"], r["w"], r["h"])
        _frames[name] = at

func _draw() -> void:
    draw_texture(_frames["hero_idle"], Vector2(64, 64))
```

Project settings that matter:

- Import the PNG as **Lossless** (compressed lossy VRAM textures create banding on 3-bit channels).
- Texture filter **Off** on the import dialog *and* `Rendering > Textures > Canvas Textures > Default Texture Filter = Nearest`. Linear filtering on a small atlas smears neighbouring sprites into each other.
- The packer leaves a 1px transparent gutter **between** frames (none around the
  sheet edge), which is enough for `AtlasTexture` regions at scale 1 with
  nearest filtering; shrink a region never - that shifts every frame by a pixel.

Animation across files (`coin_0..coin_3`) is a `SpriteFrames` build step, not a format feature - group by stem prefix and trailing integer.

---

## Pygame

```python
import json, pygame

class VpeSheet:
    def __init__(self, png, js):
        self.sheet = pygame.image.load(png).convert_alpha()
        meta = json.load(open(js, encoding="utf-8"))
        self.rects = {f["filename"].rsplit(".", 1)[0]:
                      pygame.Rect(f["textureRect"]["x"], f["textureRect"]["y"],
                                  f["textureRect"]["w"], f["textureRect"]["h"])
                      for f in meta["frames"]}

    def image(self, name, scale=1):
        src = self.sheet.subsurface(self.rects[name])
        if scale == 1:
            return src
        out = pygame.transform.scale_by(src, scale)   # pygame >= 2.3; nearest by default
        return out
```

- `pygame.Surface.set_at` / `blit` is per-pixel; blit subsurfaces instead of copying.
- Never `pygame.transform.smoothscale` - it destroys the pixel grid.
- `convert_alpha()` requires the surface loaded after `display.set_mode()`; loading earlier silently drops the per-pixel alpha.

Direct `.vpe` decode (no PNG in the loop):

```python
import struct

def vpe_to_surface(path):
    b = open(path, "rb").read()
    assert b[:8] == b"VPE565\x01\x00", "not VPE565"
    w, h, payload = struct.unpack_from("<HHI", b, 8)
    assert payload == w * h * 2 and len(b) == 16 + payload
    px = struct.unpack_from(f"<{w*h}H", b, 16)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for i, v in enumerate(px):
        s.set_at((i % w, i // w), ((v >> 11) * 8, ((v >> 5) & 63) * 4, (v & 31) * 8, 255))
    return s
```

Fine for a handful of tiles at load time; for thousands of pixels build the
`bytes` buffer once and use `pygame.image.frombuffer(buf, (w, h), "RGBA")`.

---

## HTML canvas / JS

```js
const atlas = new Image();
let FRAMES = {};

Promise.all([
  fetch("assets/sprites.json").then(r => r.json()),
  new Promise(res => { atlas.onload = res; atlas.src = "assets/sprites.png"; })
]).then(([json]) => {
  FRAMES = Object.fromEntries(
    json.frames.map(f => [f.filename.replace(/\.vpe$/, ""), f])
  );
});

const draw = (ctx, name, x, y, scale = 1) => {
  const r = FRAMES[name].textureRect;
  ctx.imageSmoothingEnabled = false;               // required for crisp pixels
  ctx.drawImage(atlas, r.x, r.y, r.w, r.h, x, y, r.w * scale, r.h * scale);
};
```

CSS alternative for small HUD pieces - a sprite as a background with integer
`background-position`, plus `image-rendering: pixelated` on the element.

Embed `header --lang js` output when you must avoid an image request (icons in a
single-file tool):

```js
const HERO_IDLE = { name: "hero_idle", width: 16, height: 16, pixels: [0xF75E, /* ... */] };

function toImageData(o) {                       // decode RGB565 -> RGBA
  const d = new ImageData(o.width, o.height);
  for (let i = 0; i < o.pixels.length; i++) {
    const v = o.pixels[i];
    d.data[i * 4]     = (v >> 11) * 8;
    d.data[i * 4 + 1] = ((v >> 5) & 63) * 4;
    d.data[i * 4 + 2] = (v & 31) * 8;
    d.data[i * 4 + 3] = v === 0xFFFF ? 0 : 255; // editor's white-is-transparent rule
  }
  return d;
}
// putImageData is not scaled/smoothed - draw it to an offscreen canvas, then
// drawImage() that canvas with imageSmoothingEnabled = false.
```

Note: `putImageData` ignores `imageSmoothingEnabled` and any transform, which is
why the offscreen-canvas step is mandatory for scaled pixel art.

---

## Unity (C#)

Prefer the baked PNG route:

1. Drop `sprites.png` + `sprites.json` under `Assets/`.
2. Texture Type **Sprite (2D and UI)**, Pixel Compression **None**/*Normal*,
   Filter Mode **Point**, Compression **None**, Mip Maps **off**, Sprite Mode
   **Multiple**.
3. Sprite Editor *Generate Insets* won't know the JSON rects - assign sprites by
   name from a small editor script:

```csharp
using UnityEngine;
using UnityEditor;

public static class VpeSpriteFiller
{
    // Build a sprite-name -> Rect table from sprites.json (textureRect), then:
    public static void Apply(SpriteTextureImporter imp, string jsonName, Rect r)
    {
        var s = new SpriteMetaItem { name = jsonName, pivot = new Vector2(.5f, .5f),
                                     border = Vector4.zero, rect = r };
        var list = new System.Collections.Generic.List<SpriteMetaItem>(imp.spritesheet);
        list.Add(s);
        imp.spritesheet = list.ToArray();
        EditorUtility.SetDirty(imp);
    }
}
```

Runtime atlas lookup without sprites (direct `.vpe` in a `TextAsset`):

```csharp
public static Texture2D FromVpe(byte[] b) {
    if (b.Length < 16 || System.Text.Encoding.ASCII.GetString(b, 0, 6) != "VPE565"
        || b[6] != 1 || b[7] != 0) throw new System.IO.InvalidDataException("bad VPE565");
    int w = System.BitConverter.ToUInt16(b, 8), h = System.BitConverter.ToUInt16(b, 10);
    int payload = System.BitConverter.ToInt32(b, 12);
    if (payload != w * h * 2 || b.Length != 16 + payload) throw new System.IO.InvalidDataException("size mismatch");
    var tex = new Texture2D(w, h, TextureFormat.RGB565, false);   // native format, no conversion
    var cols = new Color32[w * h];
    for (int i = 0; i < w * h; i++) {
        ushort v = System.BitConverter.ToUInt16(b, 16 + i * 2);
        cols[i] = new Color32((byte)(((v >> 11) & 31) * 8), (byte)(((v >> 5) & 63) * 4),
                              (byte)((v & 31) * 8), 255);
    }
    tex.SetPixels32(cols);          // Unity rows are bottom-up: flip y if you fill per row
    tex.Apply(false, false);
    return tex;
}
```

`TextureFormat.RGB565` exists but Unity expects the *byte order and row origin*
of its own convention - going through `Color32` is the portable path. Remember
Unity's texture rows start at the **bottom**, while VPE rows start at the top;
feeding them straight in gives a vertically mirrored sprite.

---

## C / MRE / LuaS30 (embedded, no image library)

This is the reference implementation's home target, and the cheapest route: the
device framebuffer already is RGB565, so a `.vpe` payload is a blit source.

```c
#include "hero_idle.h"     /* from: header hero_idle.vpe --lang c */

/* 3->5/6 bit widening only if you ever need RGBA8 for a compositor */
#define RGB565_R(v)  ((((v) >> 11) & 0x1F) * 8)
#define RGB565_G(v)  ((((v) >> 5)  & 0x3F) * 4)
#define RGB565_B(v)  (((v) & 0x1F) * 8)

void blit565(unsigned short *dst, int dst_w, int x, int y, int w, int h,
             const unsigned short *src, unsigned short key)
{
    for (int j = 0; j < h; j++) {
        const unsigned short *s = src + (size_t)j * w;
        unsigned short *d = dst + (size_t)(y + j) * dst_w + x;
        for (int i = 0; i < w; i++) {
            if (s[i] != key) d[i] = s[i];   /* key = 0xFFFF for editor transparency */
        }
    }
}

/* usage */
blit565(framebuffer, fb_width, 40, 24, HERO_IDLE_W, HERO_IDLE_H, hero_idle, 0xFFFF);
```

Rules for this target:

- `key` (colour-key transparency) must be a *deliberate* value. If the artwork
  genuinely uses white, reserve a different unused index while painting, or draw
  the sprite into a pre-cleared background-colour box.
- Never `memcpy` a whole row when using colour keying; per-pixel is required.
- The header's array is `unsigned short` little-endian values already host-ready
  - don't byte-swap on ARM/x86; only swap if the target framebuffers are
  big-endian RGB565 (rare, but some LCD controllers use `RGB565_SWAPPED`).
- In LuaS30, `40_rgb565.lua`'s `decode_vpe565` returns the same table of values,
  so a `.vpe` file is portable between the desktop editor and the phone runtime
  with no re-encoding.
