#!/usr/bin/env python3
"""VXP Pixel Editor — entry point.

Run:
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the package is importable when launched from any CWD.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Imported before Qt on purpose: it is stdlib-only and can report a missing Qt.
from vpx_editor import envcheck


def make_app_icon():
    """Generate a simple pixel-grid app icon in software."""
    from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

    pm = QPixmap(64, 64)
    pm.fill(QColor("#0B0E14"))
    p = QPainter(pm)
    colors = ["#4C8DFF", "#7B61FF", "#2DD4A0", "#F5A524", "#FF5C7A", "#FFFFFF", "#E8EEF8", "#4C8DFF"]
    # 4x4 pixel logo
    for i, c in enumerate(colors):
        x = (i % 4) * 14 + 6
        y = (i // 4) * 14 + 6
        p.fillRect(x, y, 12, 12, QColor(c))
    p.end()
    return QIcon(pm)


def run_gui() -> int:
    from PySide6.QtCore import Qt, QCoreApplication
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from vpx_editor import bootstrap
    from vpx_editor.main_window import MainWindow
    from vpx_editor.paths import ensure_layout
    from vpx_editor.theme import get_theme

    QCoreApplication.setOrganizationName("VXP")
    QCoreApplication.setApplicationName("PixelEditor")
    QCoreApplication.setApplicationVersion("1.0.0")

    # High-DPI friendly defaults
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Prefer a real installed font; QSS must not set font-family (breaks glyphs).
    font = QFont("Segoe UI")
    if not font.exactMatch():
        font = QFont("Arial")
    font.setPointSize(10)
    app.setFont(font)
    app.setWindowIcon(make_app_icon())

    # APPDATA + Documents\VPE Pixel (created on first launch / exe start)
    ensure_layout()
    get_theme().apply_to_app(app)

    # Only opens a window when something required is missing.
    if not bootstrap.preflight():
        return 1

    window = MainWindow()
    window.show()
    return app.exec()


def main() -> int:
    if not envcheck.ensure_runtime():
        return 1
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
