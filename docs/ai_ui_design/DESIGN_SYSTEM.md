# Design System — VXP Pixel Editor UI

Tokens and rules for both **Dark** (default) and **Light** themes.
Keep these in sync with `vpx_editor/theme.py` and `style/*.qss`.

---

## 1. Color tokens

### Dark (default)

| Token | Hex | Use |
|-------|-----|-----|
| `bg` | `#0B0E14` | Window background |
| `surface` | `#121722` | Cards, rails, menus |
| `surface2` | `#1A2130` | Raised controls |
| `surface3` | `#243044` | Hover / stronger chrome |
| `border` | `#2A3448` | Default borders |
| `border_soft` | `#1E2738` | Dividers |
| `text` | `#E8EEF8` | Primary text |
| `muted` | `#8A97AD` | Secondary text |
| `faint` | `#5B6A82` | Disabled |
| `accent` | `#4C8DFF` | Primary action / focus |
| `accent_hover` | `#6AA0FF` | Hover accent |
| `accent_down` | `#3A74E0` | Pressed accent |
| `accent2` | `#7B61FF` | Secondary accent |
| `ok` | `#2DD4A0` | Success |
| `warn` | `#F5A524` | Warning |
| `danger` | `#FF5C7A` | Destructive |
| `canvas_bg` | `#1E2430` | Canvas host |
| `canvas_border` | `#3A4860` | Art board edge |
| `grid` | `#3A4860` | Pixel grid lines |
| `tool_idle` | `#1A2130` | Tool button rest |
| `tool_hover` | `#243044` | Tool button hover |
| `tool_active` | `#2E4A78` | Tool button checked |
| `status` | `#0E131C` | Status bar |
| `input` | `#0F141E` | Inputs |
| `check_a` / `check_b` | `#1A2130` / `#222B3C` | Checkerboard |

### Light

| Token | Hex |
|-------|-----|
| `bg` | `#EEF1F6` |
| `surface` | `#FFFFFF` |
| `surface2` | `#F4F6FA` |
| `surface3` | `#E4EAF3` |
| `border` | `#D0D8E6` |
| `text` | `#1A2233` |
| `muted` | `#5B6A82` |
| `accent` | `#2F6FED` |
| `canvas_bg` | `#E8EDF5` |
| `check_a` / `check_b` | `#E8EDF5` / `#DDE5F0` |

Full maps live in `vpx_editor/theme.py` (`DARK`, `LIGHT`).

---

## 2. Typography

| Role | Spec |
|------|------|
| Family | Segoe UI → Arial (set in `main.py` only) |
| Body | 13px / 400 |
| Title | 18px / 600 |
| Heading (panel) | 11px / 600, uppercase via QSS-free (`SectionLabel`) |
| Status | 12px / 400 |
| Hex / coords | Consolas / Cascadia Mono if available |

**Never** set `font-family` lists in QSS (Qt breaks glyph resolution).

---

## 3. Spacing & radius

| | |
|--|--|
| Grid unit | 4px |
| Card padding | 14px |
| Panel gap | 12px |
| Control padding | 6–10px |
| Radius sm | 6px (inputs) |
| Radius md | 8px (buttons) |
| Radius lg | 10–12px (cards, tools) |

---

## 4. Elevation (shadows)

- `ShadowCard`: `QGraphicsDropShadowEffect` blur 28, offset (0, 6), black 55
- Canvas art board: layered soft rects (signature drop shadow)
- No heavy glow on idle controls; hover uses `accent` border only

---

## 5. Components

| Component | Object name / class | Notes |
|-----------|---------------------|-------|
| Tool rail button | `ToolRailButton` | 52×48, checked = `tool_active` |
| Side card | `ShadowCard` / `#Card` | Title `#Heading` |
| Accent CTA | `AccentButton` / `#Primary` | Blue fill |
| Ghost button | `#Ghost` | Theme toggle, grid, swap |
| Palette | `PaletteGrid` | 8×2 swatches, selected = accent ring |
| Size chips | `SizeSelector` | 1–5 |
| Info chip | `InfoChip` | Key + value in status/doc card |
| Color preview | `ColorPreview` | Hex + raw RGB565 |

---

## 6. Canvas view rules

| Mode | Behavior |
|------|----------|
| **BG** on | Checker bed under sprite |
| **BG** off | Flat `canvas_bg` under sprite |
| **No BG** on | `0xFFFF` white → transparent preview |
| **Grid** on | 1px lines when zoom ≥ 4 |
| Zoom | 1×–64×, 12× default fit bias |
| Pan | Middle / right drag |

---

## 7. QSS authoring rules

1. Use `@token` placeholders; never hard-code hex in `*.qss` (except `#FFFFFF` text on accent).
2. Token replace is **longest-first** (`@surface2` before `@surface`).
3. Supported: `background`, `color`, `border`, `border-radius`, `padding`, `font-size`, `font-weight`, `image: none`.
4. Unsupported / avoid: `text-transform`, multi-family `font-family`, CSS variables.
5. Every theme change goes through `Theme.apply_to_app(app)` (QSS + `QPalette`).

---

## 8. Motion

| Moment | Behavior |
|--------|----------|
| Window open | Opacity 0 → 1 (~200ms timer) |
| Canvas mount | Shadow opacity animation (`QPropertyAnimation`) |
| Theme switch | Instant palette + stylesheet swap (no cross-fade required) |
| Tool select | Checked state only (no bounce) |

Keep animation cheap — this is a pixel tool, not a marketing site.

---

## 9. Do / Don’t

| Do | Don’t |
|----|-------|
| Dark default for editors | Pure `#000` backgrounds |
| 1px borders + soft shadow | Nested heavy shadows |
| Accent only for focus/CTA | Rainbow panels |
| Checker for transparency | Fake alpha on RGB565 save |
| Match Lua palette hexes | Invent new “brand” colors in sprites |
