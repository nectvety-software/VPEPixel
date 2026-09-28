#!/usr/bin/env python3
"""VXP Pixel Editor installer — single-file wizard with environment gate.

Built by installer/setup.spec into `Setup VXP Pixel Editor.exe`, which embeds the
one-file application build under `payload/`. Running the produced exe with
`--uninstall` removes the install (files, shortcuts, Control Panel entry);
`--quiet` performs an unattended install into the default location.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import winreg
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from vpx_editor import APP_NAME, __version__, bootstrap, envcheck, icons
from vpx_editor.theme import get_theme

APP_TITLE = APP_NAME
PUBLISHER = "VXP"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VXP Pixel Editor"
EXE_NAME = "VXP Pixel Editor.exe"
UNINSTALL_NAME = "Uninstall VXP Pixel Editor.exe"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def default_target() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Programs" / APP_TITLE


def payload_dir() -> Path:
    """Where the embedded application build lives (frozen) or the dev output."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "payload"
    root = Path(__file__).resolve().parent.parent
    return root / "output" / "onefile"


def self_exe() -> Optional[Path]:
    if envcheck.is_frozen():
        return Path(sys.executable).resolve()
    return None


def desktop_dir() -> Path:
    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
                ) as key:
            raw, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(str(raw)))
    except OSError:
        return Path.home() / "Desktop"


def start_menu_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


# ---------------------------------------------------------------------------
# side effects
# ---------------------------------------------------------------------------

def _ps(script: str) -> bool:
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                               "-Command", script], capture_output=True, text=True,
                              creationflags=NO_WINDOW, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def make_shortcut(lnk: Path, target: Path, args: str, description: str) -> bool:
    """WScript.Shell through PowerShell — pywin32 is not a build dependency.

    The shell can refuse the first write while antivirus or the folder-cache
    settles, so the save is retried a few times before it is reported as failed.
    """
    lnk.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$ws = New-Object -ComObject WScript.Shell;"
        f"$s = $ws.CreateShortcut('{_q(str(lnk))}');"
        f"$s.TargetPath = '{_q(str(target))}';"
        f"$s.Arguments = '{_q(args)}';"
        f"$s.WorkingDirectory = '{_q(str(target.parent))}';"
        f"$s.Description = '{_q(description)}';"
        f"$s.IconLocation = '{_q(str(target))},0';"
        "$s.Save()"
    )
    for attempt in range(4):
        if _ps(script) and lnk.is_file():
            return True
        time.sleep(0.4 * (attempt + 1))
    return lnk.is_file()


def _q(text: str) -> str:
    """Quote for a single-quoted PowerShell string literal."""
    return text.replace("'", "''")


def remove_shortcut(lnk: Path) -> None:
    try:
        if lnk.is_file():
            lnk.unlink()
    except OSError:
        pass


def write_registry(target: Path) -> bool:
    exe = target / EXE_NAME
    uninstall = target / UNINSTALL_NAME
    command = (f'"{uninstall}" --uninstall' if uninstall.is_file()
               else f'"{exe}" --uninstall')
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_TITLE)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, __version__)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, command)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f"{exe},0")
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD,
                              _dir_size_kb(target))
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        return True
    except OSError:
        return False


def remove_registry() -> None:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    except OSError:
        pass


def installed_location() -> Optional[Path]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY) as key:
            raw, _ = winreg.QueryValueEx(key, "InstallLocation")
        return Path(str(raw))
    except OSError:
        return None


def _dir_size_kb(folder: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total // 1024


# ---------------------------------------------------------------------------
# install / uninstall workers
# ---------------------------------------------------------------------------

def _copy_file(item: Path, out: Path) -> None:
    # Defender/SmartScreen can hold a just-written 48 MB exe open for a moment.
    for attempt in range(6):
        try:
            shutil.copy2(str(item), str(out))
            return
        except PermissionError:
            if attempt == 5:
                raise PermissionError(
                    f"{out} is locked - close VXP Pixel Editor and run Setup again"
                ) from None
            time.sleep(0.5 * (attempt + 1))


class _Job(QThread):
    line = Signal(str)
    progress = Signal(int, int)
    done = Signal(bool, str)

    def __init__(self, target: Path, desktop: bool, menu: bool, parent=None) -> None:
        super().__init__(parent)
        self.target = target
        self.desktop = desktop
        self.menu = menu

    def run(self) -> None:
        try:
            self._install()
        except Exception as exc:            # surfaced in the log pane
            self.done.emit(False, f"{exc.__class__.__name__}: {exc}")

    def _install(self) -> None:
        src = payload_dir()
        exe = src / EXE_NAME
        if not exe.is_file():
            self.done.emit(False, f"payload missing: {exe}")
            return
        self.target.mkdir(parents=True, exist_ok=True)
        self.line.emit(f"installing to {self.target}")
        total = _dir_size_kb(src) * 1024
        self._copy_tree(src, self.target, total)

        me = self_exe()
        uninstaller = self.target / UNINSTALL_NAME
        if me is not None and uninstaller.is_file() and os.path.samefile(
                str(me), str(uninstaller)):
            self.line.emit("already the uninstaller - keeping this copy")
        elif me is not None:
            self.line.emit(f"copying uninstaller -> {UNINSTALL_NAME}")
            try:
                _copy_file(me, uninstaller)
            except OSError as exc:
                self.line.emit(f"  uninstaller copy failed: {exc}")
        else:
            self.line.emit("running from source — no uninstaller copy")

        (self.target / "install.json").write_text(json.dumps({
            "name": APP_TITLE, "version": __version__,
            "target": str(self.target), "publisher": PUBLISHER,
        }, indent=2), encoding="utf-8")

        if self.menu:
            path = start_menu_dir() / f"{APP_TITLE}.lnk"
            self.line.emit(f"start menu shortcut -> {path}")
            ok = make_shortcut(path, self.target / EXE_NAME, "",
                               f"{APP_TITLE} {__version__}")
            self.line.emit("  created" if ok else "  FAILED")
        if self.desktop:
            path = desktop_dir() / f"{APP_TITLE}.lnk"
            self.line.emit(f"desktop shortcut -> {path}")
            ok = make_shortcut(path, self.target / EXE_NAME, "",
                               f"{APP_TITLE} {__version__}")
            self.line.emit("  created" if ok else "  FAILED")

        self.line.emit("registry entry (Add/Remove Programs)"
                       + (" written" if write_registry(self.target) else " FAILED"))
        self.progress.emit(1, 1)
        self.done.emit(True, str(self.target))

    def _copy_tree(self, src: Path, dst: Path, total: int) -> None:
        done = 0
        for item in sorted(src.rglob("*")):
            if item.is_dir():
                continue
            rel = item.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            size = item.stat().st_size
            self.line.emit(f"copy {rel} ({size // (1024 * 1024)} MB)")
            _copy_file(item, out)
            done += size
            self.progress.emit(min(done, total), max(total, 1))


class _RemoveJob(QThread):
    line = Signal(str)
    done = Signal(bool, str)

    def __init__(self, target: Path, parent=None) -> None:
        super().__init__(parent)
        self.target = target

    def run(self) -> None:
        t = self.target
        if not t.exists():
            self.done.emit(True, f"nothing to remove ({t})")
            return
        self.line.emit("removing shortcuts and the Control Panel entry")
        remove_shortcut(desktop_dir() / f"{APP_TITLE}.lnk")
        remove_shortcut(start_menu_dir() / f"{APP_TITLE}.lnk")
        remove_registry()
        self.line.emit("removing program files")
        me = Path(sys.executable).resolve() if envcheck.is_frozen() else None
        locked = False
        for item in sorted(t.rglob("*"), reverse=True):
            if item.is_dir():
                try:
                    if not any(item.iterdir()):
                        item.rmdir()
                except OSError:
                    locked = True
                continue
            if me is not None and item.resolve() == me:
                locked = True     # a running exe cannot delete itself
                continue
            try:
                item.unlink()
            except OSError:
                locked = True
        if locked:
            self.line.emit("deferring the locked files to a detached cleanup")
            _deferred_remove(t)
        else:
            try:
                t.rmdir()
            except OSError:
                pass
        self.done.emit(True, str(t))


def _deferred_remove(target: Path) -> bool:
    """Delete the install folder after this process exits.

    The path travels in the environment, never inside the script text, so a
    folder name can never turn into PowerShell code.
    """
    env = os.environ.copy()
    env["VPE_UNINSTALL_DIR"] = str(target)
    script = (
        "$t=$env:VPE_UNINSTALL_DIR; $end=(Get-Date).AddSeconds(45);"
        "Start-Sleep -Seconds 2;"
        "while((Get-Date) -lt $end){ try{ Remove-Item -LiteralPath $t -Recurse -Force;"
        "break } catch { Start-Sleep -Milliseconds 500 } }"
    )
    # CREATE_NO_WINDOW only: adding DETACHED_PROCESS makes powershell.exe exit
    # without running the script at all.
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive",
                          "-Command", script], env=env, creationflags=NO_WINDOW,
                         close_fds=True)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# wizard ui
# ---------------------------------------------------------------------------

def _emit(text: str) -> None:
    """Quiet-mode output: console when there is one, plus VPE_SETUP_LOG if set."""
    if sys.stdout is not None:
        print(text, flush=True)
    log = os.environ.get("VPE_SETUP_LOG")
    if log:
        try:
            with open(log, "a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError:
            pass


def _button(text: str, icon_name: str, tooltip: str, kind: str = "ghost") -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName({"ghost": "Ghost", "primary": "Primary",
                       "danger": "Danger"}[kind])
    btn.setMinimumHeight(36)
    icons.set_icon(btn, icon_name, 15,
                   token="on_accent" if kind != "ghost" else "text",
                   tooltip=tooltip)
    return btn


class Wizard(QWidget):
    def __init__(self, checks: List[envcheck.Check]) -> None:
        super().__init__()
        self.checks = checks
        self.job: Optional[_Job] = None
        self._worker: Optional[bootstrap.RepairWorker] = None
        self._payload_size: Optional[int] = None
        self.setWindowTitle(f"{APP_TITLE} {__version__} — Setup")
        self.resize(660, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        title = QLabel(APP_TITLE)
        title.setObjectName("Title")
        head.addWidget(title)
        head.addStretch(1)
        self.step_label = QLabel("")
        self.step_label.setObjectName("Muted")
        head.addWidget(self.step_label)
        root.addLayout(head)

        nav = QHBoxLayout()
        self.quit_btn = _button("Quit", "close", "Close the installer", "ghost")
        self.quit_btn.clicked.connect(self.close)
        nav.addWidget(self.quit_btn)
        nav.addStretch(1)
        self.back_btn = _button("Back", "undo", "Previous step", "ghost")
        self.back_btn.clicked.connect(self._back)
        nav.addWidget(self.back_btn)
        self.next_btn = _button("Next", "check", "Continue", "primary")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)

        self.pages = QStackedWidget()
        root.addWidget(self.pages, 1)
        root.addLayout(nav)

        self.page_intro = self._intro_page()
        self.page_env = self._env_page()
        self.page_location = self._location_page()
        self.page_install = self._install_page()
        self.page_done = self._done_page()
        for p in (self.page_intro, self.page_env, self.page_location,
                  self.page_install, self.page_done):
            self.pages.addWidget(p)

        self._show(0)

    # ---- pages ----------------------------------------------------------
    def _intro_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        body = QLabel(
            f"<b>{APP_TITLE} {__version__}</b><br><br>"
            "A pixel editor for the VPE565 asset format used by VQEAF_OS.<br>"
            "The next page verifies this machine before anything is copied.")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(body)
        self.desk_check = QCheckBox("Create a desktop shortcut")
        self.desk_check.setChecked(True)
        self.desk_check.setToolTip("Adds a link to this program on the desktop")
        self.menu_check = QCheckBox("Add to the Start Menu")
        self.menu_check.setChecked(True)
        self.menu_check.setToolTip("Adds this program to the Start Menu programs list")
        lay.addWidget(self.desk_check)
        lay.addWidget(self.menu_check)
        lay.addStretch(1)
        return page

    def _env_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        note = QLabel("Required components are checked automatically. Anything "
                      "with a Fix button can be repaired from here.")
        note.setObjectName("Muted")
        note.setWordWrap(True)
        lay.addWidget(note)
        self.check_list = bootstrap.CheckList(self.checks, self._fix_one, page)
        lay.addWidget(self.check_list, 1)
        t = get_theme().tokens
        self.env_log = QPlainTextEdit()
        self.env_log.setReadOnly(True)
        self.env_log.setMaximumHeight(96)
        self.env_log.hide()
        self.env_log.setStyleSheet(
            f"background:{t['input']};color:{t['muted']};"
            f"border:1px solid {t['border']};font-size:12px;")
        lay.addWidget(self.env_log)
        self.fix_all = _button("Fix automatically", "refresh",
                               "Run every available repair in order", "primary")
        self.fix_all.clicked.connect(self._fix_all)
        row = QHBoxLayout()
        self.env_summary = QLabel("")
        self.env_summary.setObjectName("Muted")
        row.addWidget(self.env_summary, 1)
        row.addWidget(self.fix_all)
        lay.addLayout(row)
        return page

    def _location_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        note = QLabel("Choose where the program files are copied to.")
        note.setObjectName("Muted")
        lay.addWidget(note)
        line = QHBoxLayout()
        self.path_edit = QLineEdit(str(default_target()))
        self.path_edit.setToolTip("Folder that will hold the executable")
        self.path_edit.textChanged.connect(self._path_changed)
        browse = _button("Browse…", "open", "Pick another folder", "ghost")
        browse.clicked.connect(self._browse)
        line.addWidget(self.path_edit, 1)
        line.addWidget(browse)
        lay.addLayout(line)
        self.space_label = QLabel("")
        self.space_label.setObjectName("Muted")
        lay.addWidget(self.space_label)
        lay.addStretch(1)
        return page

    def _install_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        lay.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        t = get_theme().tokens
        self.log.setStyleSheet(
            f"background:{t['input']};color:{t['muted']};"
            f"border:1px solid {t['border']};font-size:12px;")
        lay.addWidget(self.log, 1)
        return page

    def _done_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 8, 4, 4)
        lay.setSpacing(10)
        self.done_title = QLabel("Installed")
        self.done_title.setObjectName("Title")
        lay.addWidget(self.done_title)
        self.done_detail = QLabel("")
        self.done_detail.setObjectName("Muted")
        self.done_detail.setWordWrap(True)
        lay.addWidget(self.done_detail)
        self.launch_check = QCheckBox("Launch VXP Pixel Editor now")
        self.launch_check.setChecked(True)
        self.launch_check.setToolTip("Start the editor when this window closes")
        lay.addWidget(self.launch_check)
        lay.addStretch(1)
        return page

    # ---- navigation -----------------------------------------------------
    def _show(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        names = ("Welcome", "Environment", "Location", "Installing", "Finished")
        self.step_label.setText(f"Step {index + 1} of {len(names)} · {names[index]}")
        self.back_btn.setEnabled(index in (1, 2))
        self.next_btn.setText({0: "Next", 1: "Next", 2: "Install",
                               3: "Next", 4: "Close"}[index])
        icons.set_icon(self.next_btn, {0: "check", 1: "check", 2: "import",
                                       3: "check", 4: "close"}[index], 15,
                       token="on_accent")
        self.next_btn.setToolTip({
            0: "Continue to the environment check",
            1: "Continue while all required checks pass",
            2: "Copy the program files now",
            3: "Finish the installation",
            4: "Close the installer",
        }[index])
        self.next_btn.setEnabled(True)
        if index == 1:
            self._sync_env()

    def _next(self) -> None:
        i = self.pages.currentIndex()
        if i == 0:
            self._show(1)
        elif i == 1:
            if envcheck.blocking(self.checks):
                self._sync_env()
                return
            self._show(2)
        elif i == 2:
            self._recheck()
            if envcheck.blocking([c for c in self.checks if c.key in ("target", "disk")]):
                self._show(1)
                self._env_line("the chosen folder cannot be used — see the "
                               "environment page")
                return
            self._start_install()
        elif i == 3:
            pass
        else:
            self._finish()

    def _back(self) -> None:
        i = self.pages.currentIndex()
        self._show(max(0, i - 1))

    # ---- environment ----------------------------------------------------
    def _payload_bytes(self) -> int:
        if self._payload_size is None:
            src = payload_dir()
            self._payload_size = (
                sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
                if src.is_dir() else 0)
        return self._payload_size

    def _sync_env(self) -> None:
        bad = envcheck.blocking(self.checks)
        can = envcheck.fixable(self.checks)
        ready = sum(1 for c in self.checks if c.ok)
        self.env_summary.setText(
            f"{ready}/{len(self.checks)} ready · "
            + (f"{len(bad)} blocking" if bad else "nothing blocking"))
        self.fix_all.setEnabled(bool(can))
        self.fix_all.setText(f"Fix automatically ({len(can)})" if can
                             else "Fix automatically")
        self.check_list.refresh()
        self.next_btn.setEnabled(not bad)

    def _recheck(self) -> None:
        fresh = envcheck.collect(Path(self.path_edit.text()), self._payload_bytes())
        by_key = {c.key: c for c in fresh}
        for c in self.checks:
            new = by_key.get(c.key)
            if new is not None:
                c.ok, c.value, c.detail = new.ok, new.value, new.detail

    def _run(self, targets: List[envcheck.Check]) -> None:
        if not targets or getattr(self, "_worker", None) is not None:
            return
        self._worker = bootstrap.RepairWorker(targets, self)
        self._worker.line.connect(self._env_line)
        self._worker.finished_all.connect(self._on_fixed)
        self.fix_all.setEnabled(False)
        self._worker.start()

    def _env_line(self, text: str) -> None:
        self.env_log.show()
        self.env_log.appendPlainText(text)

    def _fix_one(self, check: envcheck.Check) -> None:
        self._run([check])

    def _fix_all(self) -> None:
        self._run(list(envcheck.fixable(self.checks)))

    def _on_fixed(self, _fixed: int, _unresolved: int) -> None:
        self._worker = None
        self._recheck()
        self._sync_env()

    # ---- install --------------------------------------------------------
    def _browse(self) -> None:
        start = Path(self.path_edit.text())
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder",
                                                  str(start.parent if start.parent.exists()
                                                        else Path.home()))
        if folder:
            self.path_edit.setText(str(Path(folder)))

    def _path_changed(self, text: str) -> None:
        try:
            target = Path(text)
        except OSError:
            return
        need = self._payload_bytes()
        disk = envcheck.check_disk(target, need)
        self.space_label.setText(f"{disk.value}"
                                 + (f" — {disk.detail}" if disk.detail else ""))
        self.next_btn.setEnabled(disk.ok)

    def _start_install(self) -> None:
        self._show(3)
        self.log.clear()
        self.progress.setValue(0)
        self.next_btn.setEnabled(False)
        self.back_btn.setEnabled(False)
        self.quit_btn.setEnabled(False)
        self.job = _Job(Path(self.path_edit.text()), self.desk_check.isChecked(),
                        self.menu_check.isChecked())
        self.job.line.connect(self.log.appendPlainText)
        self.job.progress.connect(self._on_progress)
        self.job.done.connect(self._on_installed)
        self.job.start()

    def _on_progress(self, done: int, total: int) -> None:
        self.progress.setValue(int(done * 100 / max(total, 1)))

    def _on_installed(self, ok: bool, message: str) -> None:
        self.quit_btn.setEnabled(True)
        self.job = None
        if not ok:
            self.log.appendPlainText(f"installation failed: {message}")
            self.next_btn.setEnabled(False)
            return
        self.progress.setValue(100)
        self.done_detail.setText(f"Files are in\n{message}")
        self._show(4)

    def _finish(self) -> None:
        if self.launch_check.isChecked():
            exe = Path(self.path_edit.text()) / EXE_NAME
            if exe.is_file():
                flags = getattr(subprocess, "DETACHED_PROCESS", 0)
                try:
                    subprocess.Popen([str(exe)], cwd=str(exe.parent),
                                     creationflags=flags, close_fds=True)
                except OSError:
                    pass
        QApplication.closeAllWindows()
        self.close()


class Uninstaller(QWidget):
    def __init__(self, target: Path) -> None:
        super().__init__()
        self.target = target
        self.job: Optional[_RemoveJob] = None
        self.setWindowTitle(f"{APP_TITLE} — Uninstall")
        self.resize(460, 260)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)
        head = QLabel("Remove VXP Pixel Editor")
        head.setObjectName("Title")
        root.addWidget(head)
        detail = QLabel(f"Deletes the program files in\n{target}\n"
                        "Your .vpe assets in Documents\\VPE Pixel are not touched.")
        detail.setObjectName("Muted")
        detail.setWordWrap(True)
        root.addWidget(detail)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        root.addWidget(self.log, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = _button("Cancel", "close", "Keep the installation", "ghost")
        cancel.clicked.connect(self.close)
        go = _button("Uninstall", "delete", "Delete the program files", "danger")
        go.clicked.connect(self._start)
        row.addWidget(cancel)
        row.addWidget(go)
        root.addLayout(row)

    def _start(self) -> None:
        self.job = _RemoveJob(self.target)
        self.job.line.connect(self.log.appendPlainText)
        self.job.done.connect(self._done)
        self.job.start()

    def _done(self, ok: bool, message: str) -> None:
        self.log.appendPlainText(message if ok else f"failed: {message}")
        self.job = None


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    from PySide6.QtGui import QFont

    font = QFont("Segoe UI")
    if not font.exactMatch():
        font = QFont("Arial")
    font.setPointSize(10)
    app.setFont(font)
    get_theme().apply_to_app(app)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=f"{APP_TITLE} setup")
    parser.add_argument("--uninstall", action="store_true",
                        help="remove a previous installation")
    parser.add_argument("--quiet", action="store_true",
                        help="install without dialogs into --target")
    parser.add_argument("--target", default=None, help="installation folder")
    parser.add_argument("--no-shortcuts", action="store_true",
                        help="skip desktop / Start Menu shortcuts")
    args = parser.parse_args(argv)

    if not args.uninstall:
        me = self_exe()
        # The uninstaller is a byte copy of this binary, so double-clicking it
        # from Explorer must remove the app rather than install it again.
        args.uninstall = me is not None and me.name == UNINSTALL_NAME

    target = Path(args.target) if args.target else (installed_location()
                                                    or default_target())

    if args.quiet:
        if args.uninstall:
            removed: List[tuple] = []
            job = _RemoveJob(target)
            job.line.connect(_emit)
            job.done.connect(lambda ok, msg: (
                removed.append((ok, msg)),
                _emit(f"{'OK' if ok else 'FAILED'}: {msg}")))
            job.run()
            return 0 if removed and removed[0][0] else 1
        checks = envcheck.collect(target, 0, include_folders=False)
        bad = envcheck.blocking(checks)
        if bad:
            for c in bad:
                _emit(f"BLOCKED {c.key}: {c.detail or c.value}")
            return 2
        outcome: List[tuple] = []
        job = _Job(target, not args.no_shortcuts, not args.no_shortcuts)
        job.line.connect(_emit)
        job.done.connect(lambda ok, msg: (
            outcome.append((ok, msg)),
            _emit(f"{'OK' if ok else 'FAILED'}: {msg}")))
        job.run()                       # same thread: no event loop needed
        return 0 if outcome and outcome[0][0] else 1

    app = QApplication(sys.argv[:1])
    apply_theme(app)

    if args.uninstall:
        win = Uninstaller(target)
        win.show()
        return app.exec()

    checks = envcheck.collect(target, 0)
    win = Wizard(checks)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
