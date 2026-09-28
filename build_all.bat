@echo off
setlocal EnableExtensions
cd /d "%~dp0"

REM ============================================================
REM  One-command package build:
REM    1. app icon           installer\app.ico
REM    2. the editor         output\onefile\VXP Pixel Editor.exe   (one file)
REM    3. the installer      output\installer\Setup VXP Pixel Editor.exe
REM ============================================================

echo ============================================
echo  Build the single-file editor + its installer
echo ============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found on PATH.
    pause
    exit /b 1
)

echo [1/5] Python: %PY%
%PY% -c "import sys; print('        ', sys.version.split()[0])"

echo.
echo [2/5] Installing build tools + app deps...
%PY% -m pip install --upgrade pyinstaller -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo.
echo [3/5] Rendering installer\app.ico...
%PY% tools\make_app_icon.py 2>nul
if not errorlevel 1 goto :ico_ok
if exist "installer\app.ico" (
    echo    [warn] PIL missing - reusing the committed installer\app.ico
    goto :ico_ok
)
echo [ERROR] icon generation failed and no installer\app.ico exists.
pause
exit /b 1
:ico_ok

echo.
echo [4/5] Building the one-file editor...
%PY% -m PyInstaller --noconfirm --clean --distpath "output\onefile" --workpath "output\build_onefile" build_onefile.spec
if errorlevel 1 (
    echo [ERROR] Editor build failed.
    pause
    exit /b 1
)

echo.
echo [5/5] Building the installer...
%PY% -m PyInstaller --noconfirm --clean --distpath "output\installer" --workpath "output\build_setup" installer\setup.spec
if errorlevel 1 (
    echo [ERROR] Installer build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  BUILD OK
echo    editor    : output\onefile\VXP Pixel Editor.exe
echo    installer : output\installer\Setup VXP Pixel Editor.exe
echo.
echo  Double-click the installer, or run it unattended:
echo    "output\installer\Setup VXP Pixel Editor.exe" --quiet
echo  Uninstall from Settings - Apps, or:
echo    "%%LOCALAPPDATA%%\Programs\VXP Pixel Editor\Uninstall VXP Pixel Editor.exe" --uninstall
echo ============================================
echo.
pause
exit /b 0
