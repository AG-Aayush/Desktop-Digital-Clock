@echo off
rem Launch via the Python launcher so we get the default Python install, which
rem is where PyQt6 lives. Plain "pythonw.exe" picks whichever Python happens to
rem be first on PATH, which may not have PyQt6 -- and because pythonw has no
rem console, that failure is completely silent.
rem
rem Checks use py.exe (console launcher, returns a real exit code);
rem the actual launch uses pyw.exe so no console window sticks around.

where py.exe >nul 2>&1
if errorlevel 1 goto no_launcher

py.exe -c "import PyQt6" >nul 2>&1
if errorlevel 1 goto no_pyqt

start "" pyw.exe "%~dp0desktop_timer.py"
goto :eof

:no_launcher
echo The Python launcher (py.exe) was not found.
echo Install Python from python.org with the "py launcher" option enabled.
pause
goto :eof

:no_pyqt
echo PyQt6 is not installed for the default Python.
echo Install it with:
echo     py -m pip install PyQt6
pause
