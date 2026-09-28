# VXP Pixel Editor — Documentation

Welcome. This folder holds design, format, and delivery docs for the
Python / PySide6 pixel editor with native **VPE565** (`.vpe`) support.

## Index

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Modules, data flow, UI layout |
| [VPE_FORMAT.md](VPE_FORMAT.md) | Official VPE565 binary layout + RGB565 |
| [USER_GUIDE.md](USER_GUIDE.md) | How to draw, save, export, shortcuts |
| [ASSET_TAXONOMY.md](ASSET_TAXONOMY.md) | Which asset goes in which folder, and what VPE565 cannot represent |
| [BUILD.md](BUILD.md) | `run.bat`, `build_exe.bat`, folders, EXE |
| [ai_ui_design/](ai_ui_design/README.md) | UI design system + pixel-art reference prompts |
| [../PROMPT.md](../PROMPT.md) | Product prompt / requirements used to build the app |
| [../SKILLS.md](../SKILLS.md) | Agent skills & conventions for working in this repo |

## Quick start

```bat
run.bat
```

- Python 3.10+ and PySide6 are installed/updated automatically.
- Projects save to `Documents\VPE Pixel`.
- Settings live in `%APPDATA%\VXP Pixel Editor`.

## One-line summary

Enterprise-style dark/light pixel-art editor (Qt for Python) that opens and
saves LuaS30-compatible `.vpe` sprites — same RGB565 payload as the Nokia
S30+ **VXP Pixel Editor**.
