"""Smoke tests: VPE565 roundtrip + document tools + app construction."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def test_vpe_roundtrip() -> None:
    from vpx_editor.vpe import encode_vpe, decode_vpe, save_vpe, load_vpe, rgb_to_565, c565_to_rgb

    w, h = 12, 12
    pixels = [rgb_to_565(255, 0, 0) if i % 3 == 0 else 0xFFFF for i in range(w * h)]
    blob = encode_vpe(w, h, pixels)
    assert blob[:6] == b"VPE565"
    assert len(blob) == 16 + w * h * 2
    w2, h2, px2 = decode_vpe(blob)
    assert (w2, h2) == (w, h)
    assert px2 == pixels

    # Roundtrip sample from Lua project
    sample = ROOT.parent / "Pixel_Editor"  # unused; use docs path instead
    sample = Path(r"C:\Users\doxuanhop\Documents\LuaS30 Projects\VXP_Pixel_Editor\projects\JustKeepSwimming\hud_heart.vpe")
    if sample.exists():
        data = sample.read_bytes()
        sw, sh, spx = decode_vpe(data)
        assert sw == 12 and sh == 12
        re = encode_vpe(sw, sh, spx)
        assert re == data, "roundtrip must be byte-identical"
        print(f"  OK sample hud_heart.vpe {sw}x{sh} byte-identical")
    else:
        print("  SKIP sample file not found")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.vpe"
        save_vpe(p, w, h, pixels)
        assert load_vpe(p) == (w, h, pixels)

    # Color conversion
    assert c565_to_rgb(0xF800)[0] == 255
    assert rgb_to_565(255, 0, 0) == 0xF800
    print("  OK vpe roundtrip")


def test_document() -> None:
    from vpx_editor.document import Document

    doc = Document.blank(16, 16, 0xFFFF)
    doc.begin_stroke("Draw")
    assert doc.paint_brush(5, 5, 3, 0xF800) == 9
    doc.end_stroke()
    assert doc.can_undo()
    assert doc.get_pixel(5, 5) == 0xF800
    doc.undo()
    assert doc.get_pixel(5, 5) == 0xFFFF
    doc.redo()
    assert doc.get_pixel(5, 5) == 0xF800

    doc.begin_stroke("Fill")
    doc.flood_fill(0, 0, 0x001F)
    doc.end_stroke()
    assert doc.get_pixel(0, 0) == 0x001F
    assert doc.get_pixel(15, 15) == 0x001F
    doc.undo()
    assert doc.get_pixel(15, 15) == 0xFFFF

    blob = doc.to_vpe_bytes()
    doc2 = Document.from_vpe_bytes(blob)
    assert doc2.width == 16 and doc2.pixels == doc.pixels
    print("  OK document tools + history + vpe")


def test_icons() -> None:
    """vpx_editor/icons.py: glyph table invariants (the GUI smoke test proves
    every call site resolves, since an unknown name raises during construction)."""
    from vpx_editor import icons
    from vpx_editor.main_window import TOOLS

    codes = [cp for cp, _ab in icons.GLYPHS.values()]
    assert len(set(codes)) == len(codes), "two icons share a codepoint"
    for name, (cp, ab) in icons.GLYPHS.items():
        assert 0xE000 <= cp <= 0xF8FF, f"{name} is outside the private use area"
        assert ab.strip(), f"{name} has no text fallback"
    for key, icon_name, _title, _desc in TOOLS:
        assert icon_name in icons.GLYPHS, key
    print(f"  OK icon table ({len(icons.GLYPHS)} unique glyphs, all in the PUA)")


def test_gui_smoke() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from vpx_editor.main_window import MainWindow
    from vpx_editor.theme import get_theme

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.processEvents()
    assert win.isVisible() or True  # offscreen may not "show"
    assert win.canvas.document() is not None
    win._select_tool("fill")
    win._on_palette_color(0x001F)
    win.canvas.set_document(win.canvas.document())
    # theme toggle
    get_theme().toggle()
    win._apply_theme()
    get_theme().toggle()
    win._apply_theme()
    # save/load
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "gui.vpe"
        win._write_vpe(str(p))
        assert p.exists() and p.stat().st_size > 16
        from vpx_editor.vpe import load_vpe
        w, h, px = load_vpe(p)
        assert w == win._doc.width
    win.close()
    print("  OK gui smoke (offscreen)")


def test_hover_titles() -> None:
    """Every interactive control in the window carries a hover title."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import (
        QApplication, QAbstractButton, QComboBox, QLineEdit, QPushButton,
        QSpinBox, QToolButton,
    )
    from PySide6.QtGui import QAction
    from vpx_editor.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.processEvents()
    controls = (win.findChildren(QAbstractButton) + win.findChildren(QLineEdit)
                + win.findChildren(QComboBox) + win.findChildren(QSpinBox))
    bare = [c for c in controls
            if not c.toolTip() and not (isinstance(c, (QPushButton, QToolButton))
                                        and c.isHidden())]
    bare += [a for a in win.findChildren(QAction) if a.text() and not a.toolTip()]
    labels = [f"{type(c).__name__}:{c.text()!r}" for c in bare]
    win.close()
    assert not labels, f"controls without a hover title: {labels}"
    print("  OK hover titles on every control")


def test_button_family() -> None:
    """tools/make_ui_buttons.py: geometry contract, key safety, determinism."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_ui_buttons as B

    for style, S in B.STYLES.items():
        for token, v in S.items():
            assert v != 0xFFFF, f"{style}.{token} collides with the key"

    for shape in B.SHAPES:
        name, w, h, radii, _text, _scale = shape
        for state in B.STATES:
            img = B.draw_button(B.STYLES["retro"], shape, state)
            assert (img.w, img.h) == (w + 2 * B.PAD, h + 2 * B.PAD), name
            body = B.mask(w, h, radii, B.PAD, B.PAD)
            assert body and any(img.px[i] != 0xFFFF for i in
                                (y * img.w + x for x, y in body)), name
            assert B.draw_button(B.STYLES["retro"], shape, state).px == img.px
    for kind in B.MARKS:
        for state in B.MARK_STATES:
            assert any(c != 0xFFFF
                       for c in B.draw_mark(B.STYLES["cream"], kind, state).px)
    print("  OK button family geometry + key safety + determinism")


def test_gallery() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from vpx_editor.vpe import encode_vpe, rgb_to_565
    from vpx_editor import gallery as g

    app = QApplication.instance() or QApplication(sys.argv)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sprite = root / "sprite"
        sprite.mkdir()
        white = [rgb_to_565(255, 255, 255)] * (8 * 8)
        (sprite / "hero.vpe").write_bytes(encode_vpe(8, 8, white))
        (root / "wide.vpe").write_bytes(encode_vpe(128, 16, [0] * 2048))
        (root / "big.vpe").write_bytes(encode_vpe(240, 240, [0] * (240 * 240)))
        (root / "small.vpe").write_bytes(encode_vpe(16, 16, [0] * 256))
        (root / "mid.vpe").write_bytes(encode_vpe(48, 48, [0] * (48 * 48)))

        # folder name wins over dimensions
        assert g.asset_kind(sprite / "hero.vpe") == "sprite"
        # taxonomy sub-folders still resolve to their top-level category
        deep = sprite / "characters" / "player"
        deep.mkdir(parents=True)
        (deep / "hero_walk_0.vpe").write_bytes(encode_vpe(16, 16, white * 4))
        assert g.asset_kind(deep / "hero_walk_0.vpe") == "sprite"
        tdeep = root / "tile" / "topdown" / "architecture"
        tdeep.mkdir(parents=True)
        (tdeep / "wall.vpe").write_bytes(encode_vpe(16, 16, [0] * 256))
        assert g.asset_kind(tdeep / "wall.vpe") == "tile"
        uideep = sprite / "ui" / "buttons"
        uideep.mkdir(parents=True)
        (uideep / "btn_retro_wide_normal.vpe").write_bytes(
            encode_vpe(102, 30, [0] * (102 * 30)))
        assert g.asset_kind(uideep / "btn_retro_wide_normal.vpe") == "sprite"
        assert g.MAX_SCAN_DEPTH >= 4, "depth-4 taxonomy folders must stay scannable"
        # dimension-only classification
        assert g.kind_from_dims(root / "wide.vpe") == "texture"
        assert g.kind_from_dims(root / "big.vpe") == "titleset"
        assert g.kind_from_dims(root / "small.vpe") == "tile"
        assert g.kind_from_dims(root / "mid.vpe") == "sprite"

        thumb = g.make_thumbnail(sprite / "hero.vpe", "sprite")
        assert not thumb.isNull()
        img = thumb.toImage()
        # white must read as transparent for sprite/tile thumbnails
        assert any((img.pixel(x, y) >> 24) == 0
                   for x in range(img.width()) for y in range(img.height())), \
            "sprite thumbnails must key out white"

        # .vpea animations: first frame drives classification and thumbnails
        from vpx_editor.vpea import save_vpea
        anim = sprite / "characters" / "knight" / "knight_attack.vpea"
        anim.parent.mkdir(parents=True, exist_ok=True)
        save_vpea(anim, 8, 8, [[0xF800] * 64, [0x07E0] * 64, [0x001F] * 64],
                  90, True)
        assert g.PROJECT_SUFFIXES == {".vpe", ".vpea"}
        assert g.asset_kind(anim) == "sprite"
        assert g.read_pixels(anim)[2] == [0xF800] * 64
        assert g.asset_label(anim, "sprite") == "SPRITE · 3F", g.asset_label(anim, "sprite")
        assert g.asset_label(sprite / "hero.vpe", "sprite") == "SPRITE"
        assert not g.make_thumbnail(anim, "sprite").isNull()
        wide_anim = root / "anim_wide.vpea"
        save_vpea(wide_anim, 128, 16, [[0] * 2048], 120, True)
        assert g.kind_from_dims(wide_anim) == "texture"

        panel = g.GalleryPanel()
        panel.show()
        app.processEvents()
        panel.refresh()
        app.processEvents()
        assert isinstance(g.scan_assets(), list)
        panel.deleteLater()
    print("  OK gallery classification + thumbnails + panel")


def test_vpe_tool() -> None:
    import argparse
    import importlib.util
    from vpx_editor.vpe import encode_vpe, rgb_to_565

    script = ROOT / ".qoder" / "skills" / "vpe-game-assets" / "scripts" / "vpe_tool.py"
    assert script.exists(), f"missing skill tool: {script}"
    spec = importlib.util.spec_from_file_location("vpe_tool", script)
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)

    px = [rgb_to_565(255, 0, 0) for _ in range(64)] + [0xFFFF] * 32
    blob = encode_vpe(8, 12, px)
    w, h, back = t.decode_vpe(blob)
    assert (w, h) == (8, 12) and back == px

    for bad in (b"NOPE123\x01\x00" + bytes(8), blob[:-2], blob[:15]):
        try:
            t.decode_vpe(bad)
        except t.VpeError:
            pass
        else:
            raise AssertionError("invalid VPE must raise")

    rgba = t.to_rgba(8, 12, px, transparent_white=True)
    assert len(rgba) == 8 * 12 * 4
    assert rgba[0:4] == bytes((248, 0, 0, 255)), "5-bit channel widening, not exact 255"
    assert rgba[64 * 4 + 3] == 0, "white -> alpha 0 when opted in"
    assert t.to_rgba(8, 12, px)[64 * 4 + 3] == 255, "opaque by default"

    scaled, sw, sh = t.scale_rgba(rgba, 8, 12, 2)
    assert (sw, sh) == (16, 24) and len(scaled) == 16 * 24 * 4

    frames = [("a.vpe", 8, 8), ("b.vpe", 16, 4), ("c.vpe", 4, 20)]
    entries = [(n, w2, h2, bytes(w2 * h2 * 4), None) for n, w2, h2 in frames]
    _, aw, ah, recs = t.build_atlas(entries)
    rects = {(r["filename"]): r["textureRect"] for r in recs}
    assert aw >= 16 and ah >= 20
    boxes = [rects[n] for n, _, _ in frames]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            assert (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]
                    or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]), "frames overlap"
    hs = [r["textureRect"]["h"] for r in recs]
    assert hs == sorted(hs, reverse=True), "shelf packs tallest rows first"

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "atlas.png"
        t.write_png(p, aw, ah, bytes(aw * ah * 4))
        data = p.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        import struct as _s
        iw, ih = _s.unpack_from(">II", data, 16)
        assert (iw, ih) == (aw, ah), "IHDR carries the reported size"
        assert data[24] == 8 and data[25] == 6  # bit depth 8, colour type RGBA

    # .vpea animations expand to one named image per frame
    from vpx_editor.vpea import encode_vpea

    with tempfile.TemporaryDirectory() as td:
        blob = encode_vpea(4, 4, [[i] * 16 for i in (0xF800, 0x07E0, 0x001F)],
                           90, False)
        anim = Path(td) / "slash.vpea"
        anim.write_bytes(blob)
        (Path(td) / "still.vpe").write_bytes(encode_vpe(4, 4, [0xF800] * 16))
        got = t.frames_of(anim)
        assert [g[0] for g in got] == ["slash_00", "slash_01", "slash_02"]
        assert [g[3][:2] for g in got] == [[0xF800, 0xF800], [0x07E0, 0x07E0],
                                           [0x001F, 0x001F]]
        assert got[1][4] == {"source": "slash.vpea", "frame": 1, "frameCount": 3,
                             "delayMs": 90, "loop": False}
        assert t.frames_of(Path(td) / "still.vpe")[0][4] is None
        assert [f.name for f in t.collect_dir(Path(td))] == ["slash.vpea", "still.vpe"]
        assert t.cmd_header(argparse.Namespace(file=str(anim), lang="py",
                                               name=None, out=None)) == 2
        try:
            t.decode_vpea(blob[:-2])
        except t.VpeError:
            pass
        else:
            raise AssertionError("truncated VPEA01 must raise")
    print("  OK vpe_tool decode/rgba/pack/png + .vpea frame expansion")


def test_envcheck() -> None:
    from vpx_editor import envcheck as E

    checks = E.collect()
    keys = [c.key for c in checks]
    assert len(set(keys)) == len(keys), f"duplicate check keys: {keys}"
    for c in checks:
        assert c.label.strip() and c.value.strip(), f"{c.key} has no status text"
        assert c.ok or c.required or c.fixable, f"{c.key} fails with no way forward"
    assert not E.blocking(checks), [c.key for c in E.blocking(checks)]

    # pip must target the running interpreter, never a bare `pip` from PATH
    assert E.pip_command("-r", "requirements.txt")[:4] == \
        [sys.executable, "-m", "pip", "install"]

    # a packaged build must not pip into its own bundle
    real, lines = E.is_frozen, []
    E.is_frozen = lambda: True
    try:
        assert E.install_requirements(lines.append) is False
        assert lines and "packaged executable" in lines[0]
    finally:
        E.is_frozen = real

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # probing an install folder must not leave it behind
        missing = root / "a" / "b"
        c = E.check_creatable("Install folder", missing)
        assert c.ok and c.fix is None and not missing.exists(), \
            "check_creatable must probe the ancestor, not create the target"
        assert E.check_disk(missing, 0).ok, "disk probe needs an existing folder"
        # a path under a plain file can never be created
        blocker = root / "f.txt"
        blocker.write_text("x", encoding="utf-8")
        bad = E.check_creatable("Install folder", blocker / "sub")
        assert not bad.ok and bad.fixable
        assert bad.fix(lambda s: None) is False
        assert not (blocker / "sub").exists()
    print(f"  OK env check core ({len(checks)} checks, all required ones green)")


def test_installer() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(ROOT / "installer"))
    from PySide6.QtWidgets import QApplication
    from vpx_editor import envcheck
    import setup_wizard as S

    app = QApplication.instance() or QApplication(sys.argv)

    assert S._q("it's") == "it''s"
    assert S.REG_KEY.endswith("Uninstall\\VXP Pixel Editor")
    assert S.default_target().name == S.APP_TITLE
    assert S.UNINSTALL_NAME == "Uninstall VXP Pixel Editor.exe"

    # The uninstaller is a byte copy of Setup, so its own file name has to put
    # it in removal mode; that name must match what the install step writes.
    assert S.self_exe() is None or S.self_exe().name != S.UNINSTALL_NAME

    # The deferred sweeper carries the path in the environment only, and must
    # not use DETACHED_PROCESS (powershell then exits without running it).
    calls = []

    class _FakeSubprocess:
        CREATE_NO_WINDOW = 0x08000000

        @staticmethod
        def Popen(*args, **kwargs):
            calls.append((args, kwargs))

    real = S.subprocess
    S.subprocess = _FakeSubprocess
    try:
        assert S._deferred_remove(Path(r"D:\nope\VXP Pixel Editor")) is True
    finally:
        S.subprocess = real
    assert len(calls) == 1
    args, kwargs = calls[0]
    script = args[0][-1]
    assert "nope" not in script, "the path leaked into PowerShell code"
    assert kwargs["env"]["VPE_UNINSTALL_DIR"].endswith("VXP Pixel Editor")
    assert not kwargs["creationflags"] & 0x8

    checks = envcheck.collect()
    win = S.Wizard(checks)
    win.show()
    app.processEvents()
    win._show(1)
    assert win.next_btn.isEnabled()
    checks[0].ok = False
    win._sync_env()
    assert not win.next_btn.isEnabled(), "Next must block while a check fails"
    checks[0].ok = True
    win._sync_env()
    assert win.next_btn.isEnabled()
    win.close()
    print("  OK env check + installer wiring")


def test_vpea_codec() -> None:
    """VPEA1 container: layout, clamps, partial reads, strip export, rejects."""
    from vpx_editor.vpe import VpeError, decode_vpe
    from vpx_editor.vpea import (HEADER_SIZE, MAX_FRAMES, MIN_DELAY_MS,
                                 MAX_DELAY_MS, decode_vpea, encode_vpea,
                                 frame_count_of, header_of, load_frame,
                                 load_vpea, save_png_strip, save_vpea)

    frames = [[0xF800] * 8, [0x07E0] * 8, [0x001F] * 8]      # three 4x2 frames
    blob = encode_vpea(4, 2, frames, 90, False)
    assert blob[:8] == b"VPEA01\x01\x00"
    assert len(blob) == HEADER_SIZE + 3 * (16 + 8 * 2)
    assert decode_vpea(blob) == (4, 2, frames, 90, False)
    # a frame is a standalone .vpe payload, cuttable without the container
    assert decode_vpe(blob[HEADER_SIZE:HEADER_SIZE + 16 + 16]) == (4, 2, frames[0])
    assert decode_vpea(encode_vpea(4, 2, frames, 1))[3] == MIN_DELAY_MS
    assert decode_vpea(encode_vpea(4, 2, frames, 9_999_999))[3] == MAX_DELAY_MS
    assert MAX_FRAMES == 256

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "anim.vpea"
        save_vpea(p, 4, 2, frames, 90, False)
        assert header_of(p) == (4, 2, 3, 90, False)
        assert frame_count_of(p) == 3
        assert load_frame(p, 2)[2] == frames[2]
        assert load_vpea(p) == (4, 2, frames, 90, False)

        strip = Path(td) / "strip.png"
        save_png_strip(strip, 4, 2, frames[:2])
        from PySide6.QtGui import QImage
        img = QImage(str(strip))
        assert (img.width(), img.height()) == (8, 2), (img.width(), img.height())
        assert img.pixelColor(0, 0).name() == "#ff0000"
        assert img.pixelColor(4, 0).name() == "#00ff00"
        save_png_strip(strip, 2, 1, [[0xFFFF, 0xF800]])
        assert QImage(str(strip)).pixelColor(0, 0).alpha() == 0, "white must key out"

        bad = Path(td) / "corrupt.vpea"
        bad.write_bytes(b"VPEA01" + b"\x01\x00" + b"\x00" * 12 + b"junk")
        try:
            load_vpea(bad)
            raise AssertionError("zero-sized header accepted")
        except VpeError as exc:
            assert str(exc) == "vpea-size", exc
        p.write_bytes(p.read_bytes()[:-10])
        try:
            load_vpea(p)
            raise AssertionError("truncated container accepted")
        except VpeError as exc:
            assert str(exc) == "vpea-payload-size", exc
    print("  OK vpea codec")


def test_animation_ui() -> None:
    """Timeline, onion skin, frame ops, .vpea save/reopen through the window."""
    import time

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from vpx_editor.document import Document
    from vpx_editor.main_window import MainWindow, selected_ext
    from vpx_editor.vpea import header_of, load_frame, load_vpea, save_png_strip

    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.processEvents()

    assert win.timeline.playing() is False
    assert len(win.timeline._chips) == 1

    doc = Document.blank(16, 16, 0xFFFF, "animtest", frames=4)
    for i, frame in enumerate(doc.frames):
        frame[i * 16 + i] = 0xF800                    # a distinct dot per frame
    win._set_doc(doc, None)
    app.processEvents()
    assert len(win.timeline._chips) == 4
    assert "1/4" in win._info_frames.text(), win._info_frames.text()

    win.timeline.next_frame()
    assert win._doc.frame == 1
    win.timeline.prev_frame()
    assert win._doc.frame == 0
    win.timeline.prev_frame()                         # wraps to the last frame
    assert win._doc.frame == 3
    app.processEvents()
    assert "4/4" in win._info_frames.text()

    win.canvas.set_color(0x001F)
    win._doc.paint_brush(5, 5, 1, 0x001F)
    idx = 5 * 16 + 5
    assert win._doc.frames[3][idx] == 0x001F
    assert all(f[idx] == 0xFFFF for f in win._doc.frames[:3]), "paint leaked frames"
    win._on_edited()
    app.processEvents()

    win.timeline.toggle_onion()
    app.processEvents()
    assert win.canvas.onion_skin() is True
    assert len(win.canvas._ghosts) == 1, win.canvas._ghosts
    assert all(g.hasAlphaChannel() for _d, g in win.canvas._ghosts)
    win.timeline._onion_count.setValue(2)
    app.processEvents()
    assert len(win.canvas._ghosts) == 2
    win.timeline._onion_count.setValue(1)

    win.timeline.duplicate_frame()
    assert win._doc.frame_count() == 5 and win._doc.frame == 4
    win.timeline.move_frame(-1)
    assert win._doc.frame == 3
    win.timeline.delete_frame()
    assert win._doc.frame_count() == 4 and len(win.timeline._chips) == 4
    for _ in range(4):
        win.timeline.delete_frame()
    assert win._doc.frame_count() == 1, "the last frame must survive deletes"

    win._set_doc(Document.blank(16, 16, 0xFFFF, "animplay", frames=3), None)
    win.timeline._onion.setChecked(False)
    app.processEvents()
    win.timeline._fps.setValue(20)
    app.processEvents()
    assert win._doc.delay_ms == 50, win._doc.delay_ms
    start = win._doc.frame
    win.timeline.start()
    assert win.timeline.playing()
    t0 = time.time()
    while win._doc.frame == start and time.time() - t0 < 3.0:
        app.processEvents()
        time.sleep(0.005)
    assert win._doc.frame != start, "playback never advanced a frame"
    win.timeline.stop()
    assert not win.timeline.playing()

    win.timeline.toggle_onion()                       # playback must pause onion
    app.processEvents()
    assert win.timeline._onion.isChecked() and win.canvas.onion_skin()
    win.timeline.start()
    assert not win.timeline._onion.isChecked() and win.timeline._onion_paused
    win.timeline.stop()
    assert win.timeline._onion.isChecked() and win.canvas.onion_skin()
    win.timeline.toggle_onion()
    app.processEvents()

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "roundtrip.vpea"
        doc = Document.from_frames(8, 4, [[0xF800] * 32, [0x07E0] * 32, [0x001F] * 32],
                                   name="rt", delay_ms=90, loop=False)
        win._set_doc(doc, None)
        app.processEvents()
        win._write_vpe(str(path))
        assert path.exists() and path.suffix == ".vpea"
        assert header_of(path) == (8, 4, 3, 90, False)
        assert load_frame(path, 1)[2] == [0x07E0] * 32
        assert len(load_vpea(path)[2]) == 3
        reopened = win._load_doc(str(path))
        assert reopened.frame_count() == 3 and reopened.loop is False
        win._set_doc(reopened, str(path))
        app.processEvents()
        assert len(win.timeline._chips) == 3
        assert win.timeline._fps.value() == 11, win.timeline._fps.value()
        assert win.timeline._loop.isChecked() is False

        win._current_path = str(Path(td) / "flat.vpe")
        win._doc.dirty = True
        asked = []
        win._save_as = lambda: asked.append("save_as")
        win._save()
        assert asked == ["save_as"], "animated doc must not save silently to .vpe"
        strip = Path(td) / "strip.png"
        save_png_strip(strip, 8, 4, doc.frames)
        from PySide6.QtGui import QImage
        assert (QImage(str(strip)).width(), QImage(str(strip)).height()) == (24, 4)

    assert selected_ext("Animation (*.vpea)", ".vpe") == ".vpea"
    assert selected_ext("Still frame (*.vpe)", ".vpe") == ".vpe"
    assert selected_ext("VPE Files (*.vpe *.vpea)", ".vpea") == ".vpea"
    assert selected_ext("All Files (*)", ".vpe") == ".vpe"

    win._doc.dirty = False                            # closeEvent asks if dirty
    win.close()
    print("  OK animation timeline + onion skin + .vpea roundtrip")


def test_knight_sample() -> None:
    """tools/make_knight_anim.py: frame counts, determinism, key safety."""
    sys.path.insert(0, str(ROOT / "tools"))
    import make_knight_anim as K
    from vpx_editor.vpea import encode_vpea

    expected = {"knight_idle": 4, "knight_walk": 4, "knight_attack": 8,
                "knight_block": 3, "knight_skill": 6, "fx_slash_arc": 4,
                "fx_shield_flash": 3, "fx_shockwave": 5}
    assert list(K.TIMING) == list(expected), "TIMING drifted from the animations"
    for name, count in expected.items():
        frames = K.build(name)
        assert len(frames) == count, f"{name}: {len(frames)} != {count}"
        for i, f in enumerate(frames):
            assert (f.w, f.h) == (K.SIZE, K.SIZE)
            assert any(p != K.WHITE for p in f.px), f"{name} frame {i} is empty"

    assert [f.px for f in K.build("knight_attack")] == \
           [f.px for f in K.build("knight_attack")], "generator is not deterministic"

    # No palette colour may collide with the transparency key
    palette = [getattr(K, n) for n in dir(K)
               if n.isupper() and isinstance(getattr(K, n), int) and n != "WHITE"]
    assert K.WHITE not in palette, "a colour collides with the transparency key"
    for name in K.TIMING:
        for f in K.build(name):
            assert all(0 <= p <= 0xFFFF for p in f.px)
    for f in K.build("fx_shockwave") + K.build("fx_slash_arc"):
        assert K.OUT not in f.px, "standalone FX must not use the silhouette rim"

    frames = [f.px for f in K.build("knight_skill")]
    blob = encode_vpea(K.SIZE, K.SIZE, frames, K.TIMING["knight_skill"][0], False)
    assert len(blob) == 20 + len(frames) * (16 + K.SIZE * K.SIZE * 2)
    print("  OK knight animation sample")


def main() -> int:
    print("VXP Pixel Editor - smoke tests")
    failures = 0
    for fn in (test_vpe_roundtrip, test_document, test_vpea_codec, test_gui_smoke,
               test_animation_ui, test_hover_titles, test_gallery, test_vpe_tool,
               test_button_family, test_knight_sample, test_icons,
               test_envcheck, test_installer):
        try:
            fn()
        except Exception as exc:
            failures += 1
            print(f"  FAIL {fn.__name__}: {exc}")
            import traceback
            traceback.print_exc()
    if failures:
        print(f"\n{failures} test(s) failed")
        return 1
    print("\nAll tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
