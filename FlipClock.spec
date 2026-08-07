# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build definition -- folder build.

Produces dist/FlipClock/FlipClock.exe alongside its DLLs. A folder build is
used rather than --onefile because this app launches at sign-in: --onefile
unpacks ~60MB to %TEMP% on every start, which delays the clock appearing by
several seconds.

Build with:  build.bat      (or:  py -m PyInstaller --noconfirm FlipClock.spec)
"""

a = Analysis(
    ['desktop_timer.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim weight we never touch. Qt's heavier optional stacks are the bulk
    # of it; the clock only needs Widgets, Gui, Core and Network.
    excludes=[
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtQuick3D',
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtMultimedia',
        'PyQt6.QtBluetooth',
        'PyQt6.QtPositioning',
        'PyQt6.QtSql',
        'PyQt6.QtTest',
        'PyQt6.QtDesigner',
        'PyQt6.QtOpenGL',
        'PyQt6.QtCharts',
        'PyQt6.QtDataVisualization',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlipClock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # No console: this is a desktop widget, a terminal window behind it would
    # defeat the point.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='FlipClock.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='FlipClock',
)
