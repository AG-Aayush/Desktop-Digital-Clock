# Retro Flip Clock Desktop Overlay

A frameless, always-available flip-clock widget that sits on your Windows desktop. Digits are drawn with a custom `QPainter` routine styled after a split-flap display, the window is translucent and draggable, and it lives in the system tray between glances.

Built with Python and PyQt6. **Windows only** — it uses `winreg` for the start-with-Windows option.

---

## Download

Most people want the installer, not the source:

**[⬇ Download FlipClock](https://github.com/AG-Aayush/Desktop-Digital-Clock/releases/latest/download/FlipClock-Setup.exe)** · [Download page](https://ag-aayush.github.io/Desktop-Digital-Clock/)

Run it and leave *Start FlipClock automatically when Windows starts* ticked. Installation is per-user, so there's no admin prompt, and the clock appears on its own after every restart.

Windows will show a "Windows protected your PC" warning because the app isn't code-signed — click **More info → Run anyway**.

The rest of this file is for running or modifying the source.

---
To verify your download, compare it against the published checksum:

```powershell
Get-FileHash FlipClock-Setup.exe -Algorithm SHA256
```

It should match the value in `FlipClock-Setup.exe.sha256` on the release page.

## Features

- **Four clock styles** — the split-flap **Flip** original, a seven-segment **Digital** face whose LED digits flip on the same split-flap fold, a large-type **Minimal** face, and a **Terminal** panel with a prompt and blinking cursor; switch from Settings
- **Split-flap styling** — custom-painted digit tiles with a centre seam, rounded corners and a bold AM/PM marker
- **12- or 24-hour time**, with an optional seconds display
- **Adjustable opacity**, from 30% to fully opaque
- **Wallpaper mode** — pin the clock beneath every other window so it behaves like part of the desktop, or float it on top
- **Drag to reposition**; the window position is remembered between runs
- **System tray control** — show/hide, open settings, or exit
- **Start with Windows**, toggled from the settings dialog
- **Single instance** — launching it twice quietly exits instead of stacking clocks
- **Date strip** beneath the digits, e.g. `WED AUG 07`

---

## Requirements

| | |
|---|---|
| OS | Windows |
| Python | 3.9 or newer, installed with the **py launcher** option |
| Dependency | PyQt6 (see `requirements.txt`) |

Developed against PyQt6 6.10.2 / Qt 6.10.0 on Python 3.14.

---

## Installation

```bat
git clone https://github.com/AG-Aayush/Desktop-Digital-Clock.git
cd Desktop-Digital-Clock
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Dependencies live in the project's own `.venv`, not the global Python. `run_timer.bat` looks for `.venv` first and only falls back to the py launcher's default interpreter if the environment is missing.

For development work (packaging included), install the dev requirements instead:

```bat
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

---

## Running

**Double-click `run_timer.bat`** — the recommended route. It launches via `pyw.exe`, so no console window lingers behind the clock, and it checks for the py launcher and PyQt6 first, printing a clear message if either is missing.

Or run it directly:

```bat
py desktop_timer.py
```

---

## Using the clock

| Action | Result |
|---|---|
| Click and drag the clock | Move it; the position is saved |
| Hover over the clock | A red **✕** appears in the top-right |
| Click the **✕** | **Quits the application entirely** — the tray icon disappears too |
| Double-click the tray icon | Show or hide the clock |
| Right-click the tray icon | Show/Hide, Settings, Exit |

To get the clock off screen but keep it running, use **Show/Hide** from the tray — the ✕ button is a full exit, not a minimise.

---

## Settings

Right-click the tray icon and choose **Settings**.

| Setting | Default | What it does |
|---|---|---|
| Clock Style | Flip | Chooses the face: split-flap tiles, seven-segment Digital tiles, Minimal large type, or a Terminal panel |
| Time Format | 12-hour | Switches between `01:30:45 PM` and `13:30:45` |
| Show Seconds | On | Hides the seconds pair and its colon when off, narrowing the clock |
| Opacity | 95% | Window transparency, 30–100% |
| Stay on Wallpaper | On | On, the clock stays beneath all other windows. Off, it floats above them |
| Start with Windows | Off | Registers the clock to launch at sign-in |

Changes apply on **Apply**; **Cancel** discards them.

### Where settings live

Preferences are stored through `QSettings` in the Windows registry at:

```
HKEY_CURRENT_USER\Software\FlipClockOverlay\ClockApp
```

The start-with-Windows entry is separate, written as a `FlipClockOverlay` value under:

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
```

It invokes `pythonw.exe` so the clock starts silently at sign-in. Deleting either key resets that part of the configuration.

---

## Project structure

```
Desktop-Digital-Clock/
├── desktop_timer.py    # The entire application
├── run_timer.bat       # Windows launcher with dependency checks
├── build.bat           # One-command standalone build
├── build_installer.bat # Builds the app, then the Setup.exe
├── FlipClock.spec      # PyInstaller build definition
├── installer.iss       # Inno Setup installer definition
├── docs/index.html     # Download page (GitHub Pages)
├── .github/workflows/  # Tag a version, get a published release
├── make_icon.py        # Regenerates FlipClock.ico
├── FlipClock.ico       # Multi-resolution app icon
├── pyproject.toml      # Project metadata (pip install . also works)
├── requirements.txt    # Runtime dependencies
├── requirements-dev.txt# Adds PyInstaller for packaging
├── .gitignore
├── .gitattributes
└── README.md
```

`desktop_timer.py` is organised as these classes:

| Class | Role |
|---|---|
| `SingleInstance` | Binds a named local socket so a second launch detects the first and exits |
| `FlipDigit` | One custom-painted digit tile, optionally carrying the AM/PM marker |
| `SegmentFlipDigit` | A `FlipDigit` whose face is a seven-segment LED skeleton instead of a font glyph |
| `ColonSeparator` | The `:` between digit pairs |
| `FlipTimeDisplay` | The Flip style: a row of `FlipDigit` tiles and colons |
| `DigitalTimeDisplay` | The Digital style: `SegmentFlipDigit` tiles on the same flip animation |
| `MinimalTimeDisplay` | The Minimal style: large light type on a faint backdrop |
| `TerminalTimeDisplay` | The Terminal style: mono panel, `$` prompt, blinking cursor |
| `CloseButtonWidget` | The hover-revealed ✕ button |
| `SettingsDialog` | The preferences form |
| `FlipClockOverlay` | The main window — timer, tray icon, dragging, and persistence |

The clock renders at a fixed size tuned for a 16-inch laptop. This is deliberate; the digit tiles are `70 × 95` px and the layout is sized from `sizeHint()`.

---

## Building a standalone app

You can package the clock into an app that runs without Python installed.

```bat
.venv\Scripts\python -m pip install -r requirements-dev.txt
build.bat
```

The result lands in `dist\FlipClock\`. Launch `FlipClock.exe`, or right-click it and choose **Send to → Desktop** for a shortcut.

It's a **folder** build, not a single file, and deliberately so: `--onefile` unpacks roughly 60 MB into `%TEMP%` on every launch, which delays the clock by several seconds at sign-in. The folder build starts in about 0.2 s. To move or share it, zip the whole `FlipClock` folder — the `.exe` will not run without its `_internal` neighbour.

Expect around 95 MB on disk. `FlipClock.spec` excludes the Qt stacks the clock never touches (QML, WebEngine, Multimedia, SQL and friends); trimming further risks breaking the build for little gain.

### Switching autostart over to the packaged app

If "Start with Windows" was enabled while running from source, the registry still points at `pythonw.exe` and your `.py` file. Open **Settings** from the tray icon **of the packaged app**, untick **Start with Windows**, apply, then tick it again and apply. That rewrites the entry to the `.exe`.

The app handles this correctly when frozen — it registers just the executable path, with no script argument, since a packaged build has no `.py` file to point at.

### Building the installer

The folder build above is fine for your own machine, but for distribution you want a single `Setup.exe`:

```bat
winget install JRSoftware.InnoSetup
build_installer.bat
```

That builds the app and wraps it, producing `dist_installer\FlipClock-Setup.exe` — around 27 MB, down from 95 MB, because Inno Setup compresses with LZMA2.

The installer is per-user (`%LOCALAPPDATA%\Programs\FlipClock`), so it needs no admin rights, adds Start Menu entries and an uninstaller, and offers the autostart checkbox. It also **deletes the `StartupApproved` flag** on install — without that, a machine where the entry had once been disabled in Task Manager would silently refuse to autostart after reinstalling.

### Publishing a release

Tagging a version builds and publishes everything automatically via `.github/workflows/release.yml`:

```bat
git tag v1.0.1
git push origin v1.0.1
```

GitHub builds on a Windows runner, compiles the installer, and attaches it to a new Release. The asset filename must stay exactly `FlipClock-Setup.exe`, because the download page and the README link both point at `/releases/latest/download/FlipClock-Setup.exe`.

### The download page

`docs/index.html` is a self-contained download page with a live split-flap clock in it. Enable it under **Settings → Pages → Source: main branch, /docs folder**, and it publishes to `https://ag-aayush.github.io/Desktop-Digital-Clock/`. Open the file directly in a browser to preview changes.

### Changing the icon

Edit the drawing code in `make_icon.py` and run `py make_icon.py`, then rebuild. It emits a multi-resolution `.ico` (16 through 256 px); the sizes below 48 px drop the numeral, which is unreadable at that scale, and keep the tile silhouette instead.

---

## Troubleshooting

**Nothing happens on double-clicking `run_timer.bat`**
The batch file reports missing prerequisites, but only briefly if a check passes and the app then fails. Run `py desktop_timer.py` from a terminal to see the actual error.

**"PyQt6 is not installed for the default Python"**
PyQt6 landed under a different interpreter. Install it for the launcher's default: `py -m pip install PyQt6`. Confirm which one that is with `py --list`.

**"The Python launcher (py.exe) was not found"**
Reinstall Python from [python.org](https://www.python.org/downloads/) with the *py launcher* option ticked.

**The clock vanished**
Most likely hidden rather than closed — check the tray icon and pick Show/Hide. If it was moved off-screen, delete the `position` value under `HKEY_CURRENT_USER\Software\FlipClockOverlay\ClockApp` to reset it to `(100, 100)`.

**A second clock won't open**
Working as intended — the single-instance guard blocks it. Exit the first via the tray.

**The clock hides behind everything**
That's **Stay on Wallpaper**. Turn it off in Settings to float the clock above other windows.

---

## License

FlipClock is released under the [MIT License](LICENSE). The code is copyright AG-Aayush; use it, learn from it, fork it — just keep the copyright notice.
