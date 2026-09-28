# PROMPTS.md — AI UI & Pixel Art Design Prompts

Master prompts for (A) VXP Pixel Editor UI work and (B) pixel-art reference
sheet generation. Adapt slots in `[BRACKETS]` before sending to a model or
image tool.

---

## A. Application UI design

### A1. System prompt — UI implementer

```text
You are a senior desktop UI engineer building VXP Pixel Editor
(PySide6, enterprise dark theme).

Follow docs/ai_ui_design/DESIGN_SYSTEM.md exactly:
- Tokens from vpx_editor/theme.py (DARK/LIGHT), QSS via @token placeholders
- Font only via QApplication.setFont (never QSS font-family lists)
- Components: ShadowCard, ToolRailButton, PaletteGrid, SizeSelector
- Canvas toggles: BG, No BG (white transparent), Grid
- Projects → Documents\VPE Pixel; settings → %APPDATA%\VXP Pixel Editor
- Keep VPE565 byte compatibility (docs/VPE_FORMAT.md)

When adding UI: prefer editing existing panels over new windows.
Run python test_smoke.py after changes.
```

### A2. Feature brief template

```text
Feature: [name]
Goal: [one sentence]
Surface: [tool rail | side panel | menu | canvas | status bar]
States: [default / hover / checked / disabled]
Theme: must work in Dark AND Light
Interaction: [mouse / keyboard shortcut]
Acceptance:
- [ ] Looks correct at 1360×860 and 1100×720
- [ ] QSS tokens only (no hard-coded hex except #FFFFFF on accent)
- [ ] test_smoke.py green
```

### A3. Theme / polish brief

```text
Polish pass on [panel/widget].
Reference DESIGN_SYSTEM.md §5–§8.
Constraints: no font-family lists, no text-transform,
longest-first token fill, apply_to_app for palette+QSS.
Deliverable: screenshot Dark + Light + one line of what changed.
```

---

## B. Pixel art reference sheet

### B1. Layout rules (image UI)

When generating a **Pixel Art Reference** image for any subject:

**Background & chrome**
- Dark retro editor frame, slate/metal greys `#1E222A` → `#2D323E`
- Title bar: `PIXEL ART REFERENCE` (pixel/retro font)
- High contrast, clean grid alignment

**Three presentation sections**
1. **Left — Full sprite:** complete character/object, clean black outline
2. **Center — Grid zoom:** 16×16 (or native size) grid overlay, exact pixel placement
3. **Right — Enlarged view:** large scale (≥48×48 effective), highlights, two-tone shading

**Bottom left — Palette**
- Swatch grid of colors used
- Each swatch shows hex (e.g. `#2E8B57`, `#FADA5E`, `#000000`, `#E74C3C`)
- Tag: `PALETTE (RGB565)`

### B2. Style rules

| Aspect | Rule |
|--------|------|
| Style | 8-bit / 16-bit retro game sprite |
| Outlines | Bold dark/black, 1px at native res |
| Shading | Flat, two-tone highlight/shadow; light dither ok |
| Proportions | Slightly chibi/expressive for clarity on 240×320 |
| Clarity | Readable at 16×16 and 32×32 |

### B3. Master image prompt template

```text
Pixel art reference sheet UI for a [SUBJECT], retro game sprite style.
Dark UI editor frame at the top labeled "PIXEL ART REFERENCE".
Composition includes:
1. Left: Full pixel art sprite of [SUBJECT] with clean black outlines
   and vibrant colors.
2. Center: [SUBJECT] zoomed grid view showing 16x16 pixel layout overlay.
3. Right: Enlarged sprite view showing detailed highlights, two-tone
   shading, and expressive details.
4. Bottom Left: Color palette swatches labeled "PALETTE (RGB565)"
   with exact hex codes ([HEX_LIST]).
Clean, precise grid alignment, retro 16-bit arcade aesthetic,
high contrast dark theme background.
No watermarks, no extra text besides the labels above.
```

### B4. Palette checklist (RGB565-safe)

Always include when relevant:

| Role | Typical |
|------|---------|
| Outline | `#000000` |
| Base | subject mid-tone |
| Shadow | base × 0.65 |
| Highlight | base × 1.25 or white |
| Accent | 1–2 chroma hits |

Convert to RGB565 with `rgb_to_565` before shipping to S30+/VXP.

### B5. Subject fill-in examples

| Subject | Hex list starter |
|---------|------------------|
| Crocodile | `#2E8B57`, `#45A049`, `#FADA5E`, `#FFFFFF`, `#000000`, `#E74C3C` |
| Fish | `#FF6B35`, `#F7C548`, `#FFF8E7`, `#1B3A4B`, `#000000` |
| Heart HUD | `#FF5C7A`, `#E8384F`, `#FFD0D8`, `#000000` |
| UI icon | `#4C8DFF`, `#8A97AD`, `#E8EEF8`, `#0B0E14` |

### B6. Output explanation prompt (after image)

```text
Summarize the reference sheet:
- Subject and native size ([W]x[H])
- Palette table: swatch name, hex, RGB565 value (0xXXXX)
- Suggested C/Lua array snippet for S30+ if requested
- Notes: outline pixel policy, transparent color (usually white 0xFFFF)
```

---

## C. Shared style guardrails

```text
Do not invent logos, watermarks, or brand marks.
Do not bake unreadable small UI text into generated art.
Do not use photographic realism for sprite sheets.
Do keep titles and section labels exactly as specified.
Do keep RGB565 palette discipline (≤16 colors for VXP work).
```
