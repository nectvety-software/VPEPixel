# ai_ui_design — AI UI Design Pack

Design language and generation prompts for **VXP Pixel Editor**
(Python / PySide6) and for **pixel-art reference sheets** used with
Nokia S30+ / MRE / retro sprite work.

| File | Purpose |
|------|---------|
| [PROMPTS.md](PROMPTS.md) | Master prompts: app UI + pixel-art reference sheets |
| [SKILLS.md](SKILLS.md) | Agent skill definition (when/how to use) |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Tokens, QSS rules, layout grid, components |

## Two design tracks

### A. Application UI (enterprise pixel editor)
- Dark-first chrome, Light alternate
- QSS + palette tokens (`vpx_editor/theme.py`, `style/*.qss`)
- Shadows, tool rail, side cards, status chips
- Canvas: grid / BG / No BG toggles

### B. Pixel art reference generation
- Dark “PIXEL ART REFERENCE” sheet layout
- Full sprite · grid zoom · enlarged detail
- Palette swatches with hex + RGB565 tag
- Target: 16×16 / low-res clarity for 240×320 QVGA

Use **A** when changing the editor UI. Use **B** when generating sprite
reference images or documentation art.
