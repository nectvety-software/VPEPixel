# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — the editor as ONE self-contained executable.

    python -m PyInstaller --noconfirm --clean --distpath output/onefile \
        --workpath output/build_onefile build_onefile.spec

Produces output/onefile/VXP Pixel Editor.exe, the payload for installer/setup.spec.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve()  # noqa: F821  (SPECPATH is provided by PyInstaller)

block_cipher = None

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
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
    name="VXP Pixel Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "installer" / "app.ico"),
)
