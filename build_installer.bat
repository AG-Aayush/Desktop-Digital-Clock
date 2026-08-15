@echo off
rem Build the app, then wrap it in a Windows installer.
rem Output: dist_installer\FlipClock-Setup-<version>.exe
rem
rem Requires Inno Setup 6:  winget install JRSoftware.InnoSetup

rem winget may install Inno Setup per-user or machine-wide, so check both.
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC goto no_inno

echo [1/2] Building the application...
call "%~dp0build.bat" --from-installer
if errorlevel 1 goto failed

if not exist "%~dp0dist\FlipClock\FlipClock.exe" goto no_app

echo.
echo [2/2] Compiling the installer...
rem Read the version from pyproject.toml so it is defined in exactly one place.
for /f "delims=" %%v in ('"%PYTHON%" -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"') do set "APPVERSION=%%v"
if not defined APPVERSION goto failed
echo Building installer for version %APPVERSION% ...
"%ISCC%" /DAppVersion=%APPVERSION% "%~dp0installer.iss"
if errorlevel 1 goto failed

echo.
echo Done. Installer is in dist_installer\
pause
goto :eof

:no_inno
echo Inno Setup 6 was not found. Install it with:
echo     winget install JRSoftware.InnoSetup
pause
goto :eof

:no_app
echo The app was not built - dist\FlipClock\FlipClock.exe is missing.
pause
goto :eof

:failed
echo.
echo Build failed. See the output above.
pause
