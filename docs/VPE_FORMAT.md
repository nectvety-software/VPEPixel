# VPE565 Format Specification

Native project format of **VXP Pixel Editor** (LuaS30 and this Python port).
Extension: `.vpe` (still frame) and `.vpea` (animation) · Version: **1**

## Binary layout (little-endian)

| Offset | Size | Type | Field | Value |
|-------:|-----:|------|-------|-------|
| 0 | 6 | `char[6]` | Magic | `VPE565` (`56 50 45 35 36 35`) |
| 6 | 2 | `u16` | Version | `1` (`01 00`) |
| 8 | 2 | `u16` | Width | 1 … 640 |
| 10 | 2 | `u16` | Height | 1 … 640 |
| 12 | 4 | `u32` | Payload size | `width * height * 2` |
| 16 | N | `u16[]` | Pixels | RGB565, row-major, top-left origin |

**Total file size** = `16 + width * height * 2`.

There is no alpha channel and no trailing metadata.

## RGB565 pixel packing

```
15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0
 R  R  R  R  R  G  G  G  G  G  G  B  B  B  B  B
```

- Red: 5 bits, Green: 6 bits, Blue: 5 bits
- Stored as a little-endian `u16`
- `0xFFFF` = white · `0x0000` = black · `0xF800` = pure red

### Conversion (reference)

```python
def rgb_to_565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def c565_to_rgb(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 31
```

## Validation rules

A decoder MUST reject:

| Condition | Error id |
|-----------|----------|
| File shorter than 16 bytes | `vpe-truncated` |
| Magic ≠ `VPE565` or version ≠ 1 | `vpe-magic` |
| Width or height < 1 | `vpe-size` |
| Width or height > 640 | `image-too-large` |
| Payload ≠ `w*h*2` or file ≠ `16 + payload` | `vpe-payload-size` |

## VPEA01 — animation container

Extension: `.vpea` · Version: **1** · One file, N frames of the same size.

| Offset | Size | Type | Field | Value |
|-------:|-----:|------|-------|-------|
| 0 | 6 | `char[6]` | Magic | `VPEA01` |
| 6 | 2 | `u16` | Version | `1` |
| 8 | 2 | `u16` | Width | 1 … 640 |
| 10 | 2 | `u16` | Height | 1 … 640 |
| 12 | 2 | `u16` | Frame count | 1 … 256 |
| 14 | 2 | `u16` | Delay | milliseconds per frame, clamped to 10 … 60000 |
| 16 | 1 | `u8` | Loop | `1` = restart after the last frame |
| 17 | 3 | `u8[3]` | Reserved | zero |
| 20 | N | `VPE565[]` | Frames | `frame_count` complete `.vpe` payloads |

**Total file size** = `20 + frame_count * (16 + width * height * 2)`.

Every frame is a byte-exact VPE565 payload, so a frame can be sliced out with
`HEADER_SIZE + index * (16 + w*h*2)` and opened by any VPE565 decoder without
the container. The editor relies on this for the gallery thumbnails and for
`load_frame()`, which reads one frame without decoding the rest.

| Condition | Error id |
|-----------|----------|
| File shorter than 20 bytes | `vpea-truncated` |
| Magic ≠ `VPEA01` or version ≠ 1 | `vpea-magic` |
| Width, height or frame count < 1 | `vpea-size` |
| Frame count > 256 | `vpea-frames` |
| File size ≠ header + count × frame size | `vpea-payload-size` |
| A frame declares different dimensions | `vpea-frame-dims` |

`.vpe` remains single-frame and unchanged — LuaS30 never sees a `.vpea` file.
Saving an animated document to a `.vpe` path is refused by the editor and
redirected to Save As.

## Compatibility

Verified against LuaS30 sample
`projects/JustKeepSwimming/hud_heart.vpe` (12×12):

- Decode → re-encode is **byte-identical**.
- Edit-one-pixel → save → reload preserves every other pixel.

## Example header (12×12)

```
56 50 45 35 36 35   ; "VPE565"
01 00               ; version 1
0C 00               ; width 12
0C 00               ; height 12
20 01 00 00         ; payload 0x120 = 288 = 12*12*2
```

Then 288 bytes of RGB565 pixels.

## Related exports (not `.vpe`)

| Format | Use |
|--------|-----|
| BMP 24-bit | Windows bitmap, bottom-up BGR rows (4-byte padded) |
| PNG | Qt `QImage` write; white may be shown as transparent in-app (`No BG`) but PNG export writes opaque RGB |

`.vpe` is the **editable project** format. BMP/PNG are exports only.
