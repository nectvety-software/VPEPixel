@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "APP_NAME=VXP Pixel Editor"
set "OUT=output"
set "DIST_DIST=output\dist"

echo ============================================
echo  Build %APP_NAME% EXE  -^>  %OUT%\
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

echo [1/4] Python: %PY%
%PY% -c "import sys; print('   ', sys.version.split()[0])"

echo.
echo [2/4] Installing build tools + app deps...
%PY% -m pip install --upgrade pip
%PY% -m pip install --upgrade pyinstaller -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo.
echo [3/4] PyInstaller building...
if exist "%OUT%" rmdir /s /q "%OUT%"
%PY% -m PyInstaller --noconfirm --clean --distpath "%OUT%\dist" --workpath "%OUT%\build" build_exe.spec
if errorlevel 1 (
    echo [ERROR] Build failed. See messages above.
    pause
    exit /b 1
)

echo.
echo [4/4] Copying launcher + notes into %OUT%\

REM Convenience launcher next to the exe folder
> "%OUT%\Run VXP Pixel Editor.bat" (
    echo @echo off
    echo cd /d "%%~dp0dist\VXP Pixel Editor"
    echo start "" "VXP Pixel Editor.exe"
)

> "%OUT%\README-EXE.txt" (
    echo VXP Pixel Editor - portable EXE package
    echo =========================================
    echo.
    echo Run:   output\dist\VXP Pixel Editor\VXP Pixel Editor.exe
    echo    or: output\Run VXP Pixel Editor.bat
    echo.
    echo App data^:  %%APPDATA%%\VXP Pixel Editor
    echo              (settings.ini, autosave.vpe)
    echo.
    echo Projects^:  %%USERPROFILE%%\Documents\VPE Pixel
    echo              (.vpe project saves)
    echo Exports^:   %%USERPROFILE%%\Documents\VPE Pixel\exports
    echo              (BMP / PNG)
    echo.
    echo Optional install: copy the folder
    echo   "output\dist\VXP Pixel Editor"
    echo to e.g. C:\Program Files\VXP Pixel Editor
    echo and send a shortcut to the Desktop / Start Menu.
)

echo.
echo ============================================
echo  BUILD OK
echo  EXE:  %OUT%\dist\%APP_NAME%\%APP_NAME%.exe
echo  App data:  %%APPDATA%%\%APP_NAME%
echo  Projects:  Documents\VPE Pixel
echo ============================================
echo.
pause
exit /b 0
