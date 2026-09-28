@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=VXP Pixel Editor"
set "ENTRY=main.py"
set "REQ=requirements.txt"

echo ============================================
echo  %APP_NAME% - environment check ^& launch
echo ============================================
echo.

REM ---- Python ----
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    where python3 >nul 2>nul && set "PY=python3"
)
if not defined PY (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure "Add python.exe to PATH" is checked during install.
    echo.
    pause
    exit /b 1
)

echo [1/4] Using: %PY%
%PY% -c "import sys; print('Python', sys.version.split()[0]); assert sys.version_info >= (3, 10), 'Python 3.10+ required'" || (
    echo [ERROR] Python 3.10 or newer is required.
    pause
    exit /b 1
)

REM ---- pip ----
echo.
echo [2/4] Checking pip...
%PY% -m pip --version >nul 2>nul || (
    echo [WARN] pip missing - trying to bootstrap...
    %PY% -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ERROR] Could not install pip.
        pause
        exit /b 1
    )
)

REM ---- Dependencies ----
echo.
echo [3/4] Checking / updating libraries...
if exist "%REQ%" (
    %PY% -m pip install --upgrade -r "%REQ%"
) else (
    %PY% -m pip install --upgrade PySide6
)
if errorlevel 1 (
    echo [ERROR] Dependency install failed.
    pause
    exit /b 1
)

%PY% -c "import PySide6; print('PySide6', PySide6.__version__)" || (
    echo [ERROR] PySide6 is not importable after install.
    pause
    exit /b 1
)

REM ---- Folders: APPDATA + Documents\VPE Pixel ----
echo.
echo [4/5] Preparing folders...
%PY% -c "from vpx_editor.paths import ensure_layout; p=ensure_layout(); print('   app_data:', p['app_data']); print('   projects:', p['projects']); print('   exports: ', p['exports'])"

REM ---- Launch ----
echo.
echo [5/5] Launching %APP_NAME%...
echo.
%PY% "%ENTRY%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if not "%EXITCODE%"=="0" (
    echo [ERROR] %APP_NAME% exited with code %EXITCODE%.
) else (
    echo %APP_NAME% closed normally.
)
echo.
pause
exit /b %EXITCODE%
