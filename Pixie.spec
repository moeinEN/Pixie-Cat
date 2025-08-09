# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ASSETS_DIR = ROOT / "pixie" / "assets"

def msys_prefix():
    for k in ("MSYSTEM_PREFIX", "MINGW_PREFIX", "GTK_PREFIX"):
        v = os.environ.get(k)
        if v and Path(v).exists():
            return Path(v)
    for guess in ("C:/msys64/ucrt64", "C:/msys64/mingw64"):
        if Path(guess).exists():
            return Path(guess)
    return None

extra_datas = [(str(ASSETS_DIR), "pixie/assets")]

_prefix = msys_prefix()
if _prefix:
    extra_datas += [
        (str(_prefix / "lib" / "girepository-1.0"), "lib/girepository-1.0"),
        (str(_prefix / "lib" / "gdk-pixbuf-2.0"),  "lib/gdk-pixbuf-2.0"),
    ]

a = Analysis(
    ['run_pixie.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=extra_datas,
    hiddenimports=[
        'gi', 'gi._gi', 'gi.repository',
        'gi.repository.GLib', 'gi.repository.GObject', 'gi.repository.Gio',
        'gi.repository.GdkPixbuf', 'gi.repository.Gdk', 'gi.repository.Gtk',
        'gi.repository.GdkWin32'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_gi_paths.py'],
    excludes=[
        # trim some GUI stacks you don't use
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Pixie',
    icon=str(ASSETS_DIR / 'icon.ico') if (ASSETS_DIR / 'icon.ico').exists() else None,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)