@echo off
rem Build the standalone app into dist\FlipClock\.
rem
rem Uses the py launcher for the same reason run_timer.bat does: PyQt6 and
rem PyInstaller live in the default Python, which is not necessarily whichever
rem python.exe happens to be first on PATH.

where py.exe >nul 2>&1
if errorlevel 1 goto no_launcher

py.exe -c "import PyInstaller" >nul 2>&1
if errorlevel 1 goto no_pyinstaller

echo Building FlipClock...
py.exe -m PyInstaller --noconfirm FlipClock.spec
if errorlevel 1 goto failed

echo.
echo Done. The app is in dist\FlipClock\FlipClock.exe
echo Right-click it and "Send to > Desktop" for a shortcut.
pause
goto :eof

:no_launcher
echo The Python launcher (py.exe) was not found.
echo Install Python from python.org with the "py launcher" option enabled.
pause
goto :eof

:no_pyinstaller
echo PyInstaller is not installed for the default Python.
echo Install it with:
echo     py -m pip install pyinstaller
pause
goto :eof

:failed
echo.
echo Build failed. See the output above.
pause
