; Inno Setup script for FlipClock.
;
; Builds a single Setup.exe from the PyInstaller output in dist\FlipClock.
; Run build_installer.bat, which builds the app first and then compiles this.
;
; Installs per-user into %LOCALAPPDATA%\Programs so no admin rights and no UAC
; prompt are needed -- the app only ever writes to HKCU anyway.

#define AppName "FlipClock"
; Version is passed in by build_installer.bat, read from pyproject.toml.
; Falls back to 0.0.0-dev so a manual ISCC run still compiles.
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#define AppPublisher "AG-Aayush"
#define AppURL "https://github.com/AG-Aayush/Desktop-Digital-Clock"
#define AppExe "FlipClock.exe"

[Setup]
AppId={{8F3C1A94-6D2B-4E77-9C15-2A7B4E9D0F31}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Per-user install: no admin, no UAC prompt.
PrivilegesRequired=lowest
OutputDir=dist_installer
; Deliberately unversioned: it keeps
; /releases/latest/download/FlipClock-Setup.exe working as a permanent link
; on the download page. The version is carried in the release tag and in the
; installer's own version metadata.
OutputBaseFilename=FlipClock-Setup
SetupIconFile=FlipClock.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Shut the clock down before overwriting its files, so an upgrade over a
; running instance does not fail on locked DLLs.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Start {#AppName} automatically when Windows starts"; GroupDescription: "Startup:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "dist\FlipClock\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\FlipClock\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; The autostart entry itself.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "FlipClockOverlay"; \
    ValueData: """{app}\{#AppExe}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

; Windows records a separate "disabled" flag when a startup entry is switched
; off in Task Manager, and that flag survives reinstalls. Left in place it
; silently suppresses the entry above, so clear it on install.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"; \
    ValueType: none; ValueName: "FlipClockOverlay"; \
    Flags: deletevalue uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Settings live in the registry, not here, but clear the folder shell.
Type: dirifempty; Name: "{app}"
