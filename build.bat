@echo off
rem Build the standalone app into dist\FlipClock\.
rem Prefers the project's .venv; falls back to the default Python otherwise.

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
    where py.exe >nul 2>&1
    if errorlevel 1 goto no_python
    set "PYTHON=py.exe"
)

"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 goto no_pyinstaller

echo Building FlipClock with %PYTHON% ...
"%PYTHON%" -m PyInstaller --noconfirm FlipClock.spec
if errorlevel 1 goto failed

echo.
echo Done. The app is in dist\FlipClock\FlipClock.exe
echo Right-click it and "Send to > Desktop" for a shortcut.
rem Skip the prompt when chained from build_installer.bat.
if "%~1"=="--from-installer" goto :eof
pause
goto :eof

:no_python
echo No .venv found and the Python launcher (py.exe) is missing.
echo Create the environment with:
echo     py -m venv .venv
echo     .venv\Scripts\python -m pip install -r requirements-dev.txt
pause
goto :eof

:no_pyinstaller
echo PyInstaller is not installed. Install the dev requirements with:
echo     .venv\Scripts\python -m pip install -r requirements-dev.txt
pause
goto :eof

:failed
echo.
echo Build failed. See the output above.
pause
