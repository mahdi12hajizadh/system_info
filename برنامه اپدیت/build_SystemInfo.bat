@echo off
setlocal EnableExtensions

title SystemInfo - Build EXE

echo ==========================================
echo        SystemInfo EXE Builder
echo ==========================================
echo.

REM Always work from the folder where this BAT file is located.
cd /d "%~dp0"

echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python was not found.
    echo Install Python and make sure "python" works in CMD/PowerShell.
    pause
    exit /b 1
)

echo.
echo [2/4] Checking system_info_updated.py...
if not exist "system_info_updated.py" (
    echo.
    echo ERROR: system_info_updated.py was not found.
    echo Put this BAT file and system_info_updated.py in the SAME folder.
    echo.
    echo Current folder:
    cd
    echo.
    pause
    exit /b 1
)

echo.
echo [3/4] Installing/checking PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: Could not install PyInstaller.
    pause
    exit /b 1
)

echo.
echo [4/4] Building SystemInfo.exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SystemInfo "system_info_updated.py"

if errorlevel 1 (
    echo.
    echo ==========================================
    echo BUILD FAILED
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ==========================================
echo BUILD SUCCESSFUL!
echo ==========================================
echo.
echo EXE location:
echo %~dp0dist\SystemInfo.exe
echo.

if exist "%~dp0dist\SystemInfo.exe" (
    echo Opening the dist folder...
    explorer "%~dp0dist"
) else (
    echo WARNING: EXE was not found at the expected location.
)

echo.
pause
