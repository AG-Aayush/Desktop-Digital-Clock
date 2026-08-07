@echo off
rem Launch the clock, preferring the project's own .venv so the app never
rem depends on whichever Python happens to be first on PATH.
rem
rem pythonw.exe has no console, so a missing dependency there fails silently;
rem every check below therefore runs on a console interpreter first.

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    "%~dp0.venv\Scripts\python.exe" -c "import PyQt6" >nul 2>&1
    if not errorlevel 1 (
        start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0desktop_timer.py"
        goto :eof
    )
    echo The project .venv exists but PyQt6 is not installed in it.
    echo Install with:
    echo     .venv\Scripts\python -m pip install -r requirements.txt
    pause
    goto :eof
)

rem No .venv -- fall back to the default Python via the py launcher.
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
