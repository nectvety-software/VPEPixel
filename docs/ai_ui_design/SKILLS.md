---
name: vxp-ai-ui-design
description: Design and implement enterprise UI for VXP Pixel Editor (PySide6/QSS) and generate pixel-art reference sheets (retro UI, RGB565 palettes) for S30+/MRE sprites. Use for UI polish, theme tokens, canvas view modes, sprite reference images, and palette prompts.
---

# Skill: VXP AI UI Design

Two coordinated skills in one pack:

1. **App UI design** — Dark/Light enterprise chrome for the PySide6 editor  
2. **Pixel art reference generation** — Retro “PIXEL ART REFERENCE” sheets  

Read `DESIGN_SYSTEM.md` (tokens/components) and `PROMPTS.md` (templates) first.

---

## When to use

Use this skill when the user asks to:

- Design, restyle, or implement UI in **VXP Pixel Editor**
- Add QSS themes, tokens, shadows, tool rails, side panels
- Toggle canvas **background / no-background / grid** presentation
- Generate **pixel art reference sheets** or sprite design prompts
- Build **RGB565 palettes** for Nokia S30+ / MRE / VXP sprites
- Write image-gen prompts for retro sprite documentation art

---

## Workflow — App UI

1. **Read** `DESIGN_SYSTEM.md` and current `style/dark.qss` / `light.qss`.
2. **Classify** the request: new component · polish · theme · canvas view.
3. **Map tokens** — only `@token` names from `theme.py` (DARK + LIGHT).
4. **Implement** in `vpx_editor/` using existing widgets when possible
   (`ShadowCard`, `ToolRailButton`, `PaletteGrid`, …).
5. **Canvas view flags** (if relevant):

   | Toggle | Effect |
   |--------|--------|
   | BG | Checker under sprite |
   | No BG | White `0xFFFF` → transparent |
   | Grid | Pixel grid |

6. **Fonts** — `QApplication.setFont` only; never QSS `font-family` lists.
7. **Verify** — `python test_smoke.py`; Dark + Light both look correct.

## Workflow — Pixel art reference

1. **Extract** subject (`[SUBJECT]`) and 6–8 hex colors (include `#000000` outline).
2. **Fill** the master template in `PROMPTS.md` §B3 (three panels + palette).
3. **Generate** the image (or hand the prompt to an image tool).
4. **Explain** with §B6: sizes, hex table, RGB565 `0xXXXX` values, outline policy.

---

## Layout spec (reference sheets)

| Region | Content |
|--------|---------|
| Title | `PIXEL ART REFERENCE` on dark metal bar `#1E222A`–`#2D323E` |
| Left | Full sprite, black outline |
| Center | 16×16 grid overlay |
| Right | Enlarged detail, two-tone shade |
| Bottom left | Swatches + hex + `PALETTE (RGB565)` |

Style: 8/16-bit, flat shade, readable at 16×16 and 240×320.

---

## Constraints

- VPE565 project color model (no real alpha in `.vpe`)
- Classic 16-color editor palette for shared sprites when possible
- QSS: no `text-transform`, no multi-family fonts, longest-first `@` tokens
- Paths: `Documents\VPE Pixel` · `%APPDATA%\VXP Pixel Editor`
- No watermarks / fake brand logos in generated art

---

## Done means

- [ ] Matches `DESIGN_SYSTEM.md` tokens and spacing
- [ ] Dark + Light both verified
- [ ] Tests green (`test_smoke.py`)
- [ ] Reference sheets use §B3 template + hex palette
- [ ] Docs updated if UI behavior changed
