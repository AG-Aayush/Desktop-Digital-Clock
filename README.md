# Retro Flip Clock Desktop Overlay

A frameless, always-available flip-clock widget that sits on your Windows desktop. Digits are drawn with a custom `QPainter` routine styled after a split-flap display, the window is translucent and draggable, and it lives in the system tray between glances.

Built with Python and PyQt6. **Windows only** — it uses `winreg` for the start-with-Windows option.

---

## Features

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
py -m pip install -r requirements.txt
```

Use `py` rather than `python`. `run_timer.bat` launches through the py launcher, so PyQt6 must be installed for **that** interpreter — installing it under a different Python on your `PATH` will leave the clock unable to start.

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
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
```

`desktop_timer.py` is organised as five classes:

| Class | Role |
|---|---|
| `SingleInstance` | Binds a named local socket so a second launch detects the first and exits |
| `FlipDigit` | One custom-painted digit tile, optionally carrying the AM/PM marker |
| `ColonSeparator` | The `:` between digit pairs |
| `CloseButtonWidget` | The hover-revealed ✕ button |
| `SettingsDialog` | The preferences form |
| `FlipClockOverlay` | The main window — timer, tray icon, dragging, and persistence |

The clock renders at a fixed size tuned for a 16-inch laptop. This is deliberate; the digit tiles are `70 × 95` px and the layout is sized from `sizeHint()`.

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
