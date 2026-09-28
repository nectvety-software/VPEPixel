# Build & Packaging

## Scripts

| Script | What it does |
|--------|----------------|
| `run.bat` | Check Python/pip → install/update `requirements.txt` → create folders → launch |
| `build_exe.bat` | Install PyInstaller → build windowed one-folder EXE into `output\` |
| `build_all.bat` | Icon → **one-file** app EXE → **one-file** `Setup …exe` installer |

## One-file build + installer (recommended)

```bat
build_all.bat
```

Produces two single files:

```
output/
├── onefile/
│   └── VXP Pixel Editor.exe            ~46 MB, no folder, no Python needed
└── installer/
    └── Setup VXP Pixel Editor.exe      ~92 MB, contains the file above
```

`Setup VXP Pixel Editor.exe` is a 5-page wizard (Welcome → Environment →
Location → Installing → Finished). Double-clicking it is the normal path;
it can also run unattended:

```bat
"output\installer\Setup VXP Pixel Editor.exe" --quiet
"output\installer\Setup VXP Pixel Editor.exe" --quiet --target D:\Apps\VXP --no-shortcuts
"%LOCALAPPDATA%\Programs\VXP Pixel Editor\Uninstall VXP Pixel Editor.exe" --quiet
```

`--quiet` writes one line per step to stdout and, when `VPE_SETUP_LOG` is set,
to that file. Exit codes: `0` ok, `1` the job failed, `2` a required
environment check blocked it.

Quiet mode honours `--uninstall` too, and the uninstaller switches to removal
mode by its own file name — `Uninstall VXP Pixel Editor.exe` is a byte copy of
Setup, so double-clicking it must never install the app again.

What the installer writes:

| Item | Location |
|------|----------|
| Program files | `%LOCALAPPDATA%\Programs\VXP Pixel Editor` (default, changeable on page 3) |
| Uninstaller | same folder, `Uninstall VXP Pixel Editor.exe` |
| Install record | same folder, `install.json` |
| Shortcuts | Desktop + Start Menu (opt-in checkboxes on page 1) |
| Add/Remove Programs | `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\VXP Pixel Editor` |

Uninstall removes all five. The uninstaller cannot delete itself, so a locked
leftover is handed to a detached `powershell Remove-Item` retry loop
(`_deferred_remove`) that finishes within a few seconds.

## Environment check

`vpx_editor/envcheck.py` is stdlib-only and runs **before** Qt is imported, so
a missing PySide6 can still be reported (console mode, `python -m
vpx_editor.envcheck`). Once Qt is available `vpx_editor/bootstrap.py` shows the
same list as a dialog with a **Fix automatically** button.

Nine checks: Windows build, CPU arch, Python ≥ 3.10, PySide6 ≥ 6.6, VC++
runtime, APPDATA folder, Projects folder, free disk space, icon font. The last
two are informational (`required=False`); only a failing *required* check blocks
Continue. Repairs stream `pip install -r requirements.txt` for the *running*
interpreter (`python -m pip`, never a bare `pip` from PATH) and refuse to run
inside a frozen executable.

The dialog opens automatically at startup only when something required fails
(`main.py` → `bootstrap.preflight()`), and manually from
**Help → Check Environment…**. The installer embeds the same list on its
Environment page.


## Run from source

```bat
run.bat
```

Steps inside:

1. Locate `py -3` / `python` / `python3` (require 3.10+)
2. Ensure `pip` (`ensurepip` if missing)
3. `pip install --upgrade -r requirements.txt`
4. Create `APPDATA\VXP Pixel Editor` + `Documents\VPE Pixel`
5. `python main.py`

## Build EXE (one folder)

```bat
build_exe.bat
```

Or manually:

```bat
py -3 -m pip install --upgrade pyinstaller -r requirements.txt
py -3 -m PyInstaller --noconfirm --clean --distpath output\dist --workpath output\build build_exe.spec
```

Use this when you want to inspect or ship the unpacked tree; `build_all.bat`
is what you want for a single distributable file.

### Output tree

```
output/
├── dist/
│   └── VXP Pixel Editor/
│       ├── VXP Pixel Editor.exe      ← windowed GUI (no console)
│       └── _internal/
│           ├── style/dark.qss
│           ├── style/light.qss
│           └── PySide6 / shiboken6 / DLLs…
├── build/                            ← PyInstaller work dir (safe to delete)
├── Run VXP Pixel Editor.bat
└── README-EXE.txt
```

`build_all.bat` adds `onefile/`, `installer/`, `build_onefile/` and
`build_setup/` next to these.

## PyInstaller notes

| Spec | Result |
|------|--------|
| `build_exe.spec` | one folder, `console=False` |
| `build_onefile.spec` | same Analysis, `EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, …)`, no `COLLECT` |
| `installer/setup.spec` | the wizard (`installer/setup_wizard.py`) with `output/onefile/VXP Pixel Editor.exe` embedded as `payload/` |

- `console=False` — GUI only, all three
- `datas` embeds `style/*.qss` → `_internal/style/` (or `_MEIPASS/style/` in one-file)
- `installer/app.ico` is the icon for both the app and the setup file;
  regenerate it with `python tools\make_app_icon.py` (needs Pillow)
- Hidden imports: `PySide6.QtCore/QtGui/QtWidgets`
- Excludes: tkinter, numpy, pandas, matplotlib (not used)
- `installer/setup.spec` stops with the exact rebuild command if the app EXE
  is missing — build `build_onefile.spec` first

### Frozen path resolution

| Need | Resolution order |
|------|------------------|
| QSS | `sys._MEIPASS/style` → `_internal/style` → source `style/` → exe dir |
| Settings | `%APPDATA%\VXP Pixel Editor` |
| Projects | `%USERPROFILE%\Documents\VPE Pixel` |
| Installer payload | `sys._MEIPASS/payload` → `output/onefile` |

## Optional manual install

1. Copy `output\dist\VXP Pixel Editor` (or the single file from
   `output\onefile`) to e.g. `C:\Program Files\VXP Pixel Editor`
2. Create a shortcut to `VXP Pixel Editor.exe` on Desktop / Start Menu
3. App data and projects still go to APPDATA / Documents (portable-friendly)

## Tests

```bat
py -3 test_smoke.py
```

Covers VPE565 round-trip (Lua sample), document undo, offscreen GUI, gallery
classification, icon table, hover titles, the button family, `envcheck`
invariants and the installer wiring (shortcut quoting, deferred-removal script,
wizard blocking).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Python was not found` | Install Python 3.10+, check “Add to PATH” |
| White UI / missing fonts in screenshots | Prefer real desktop; offscreen platform has 0 fonts |
| QSS not dark | Do not use comma `font-family` lists; use `QApplication.setFont` |
| Token colors wrong (`#1217222`) | Longest-first token replace (see `theme._fill_tokens`) |
| EXE missing styles | Ensure the spec's `datas` includes `style/*.qss` |
| Setup: `… is locked - close VXP Pixel Editor and run Setup again` | The running exe holds the destination open; `_copy_file` already retries 6× for Defender scans |
| Setup: `payload missing: …` | `output\onefile\VXP Pixel Editor.exe` was not built — run `build_all.bat` |
| Uninstall leaves one exe behind | Expected mid-run: the detached sweeper deletes it seconds later; `DETACHED_PROCESS` must stay out of its `creationflags` or PowerShell exits silently |
| Shortcut not created | Windows refuses a `.lnk` whose target is not a real PE file; check the target path on page 3 |

