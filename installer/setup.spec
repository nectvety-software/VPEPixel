# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — the single-file installer.

    python -m PyInstaller --noconfirm --clean --distpath output/installer \
        --workpath output/build_setup installer/setup.spec

Embeds output/onefile/VXP Pixel Editor.exe as `payload/`, so the result is one
hostable file: Setup VXP Pixel Editor.exe.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821  (project root)
PAYLOAD = ROOT / "output" / "onefile" / "VXP Pixel Editor.exe"

if not PAYLOAD.is_file():
    raise SystemExit(
        f"missing application build: {PAYLOAD}\n"
        "build it first:  python -m PyInstaller --noconfirm --clean "
        "--distpath output/onefile --workpath output/build_onefile build_onefile.spec")

block_cipher = None

a = Analysis(
    [str(Path(SPECPATH) / "setup_wizard.py")],  # noqa: F821
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(PAYLOAD), "payload"),
        (str(ROOT / "style" / "dark.qss"), "style"),
        (str(ROOT / "style" / "light.qss"), "style"),
    ],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas", "PIL",
        "scipy", "IPython", "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Setup VXP Pixel Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # the wizard is a GUI; --quiet just prints nothing
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "installer" / "app.ico"),
)
