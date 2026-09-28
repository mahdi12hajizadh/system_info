@echo off
REM ============================================
REM  Build script: turns system_info_gui.py into
REM  a single-file Windows .exe using PyInstaller
REM ============================================

echo Installing/updating dependencies...
pip install -r requirements.txt

echo.
echo Building the .exe ...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "SystemInfoViewer" ^
    --icon "app_icon.ico" ^
    --version-file "version_info.txt" ^
    system_info.py

echo.
echo Done! Your .exe is in the "dist" folder: dist\SystemInfoViewer.exe
pause
