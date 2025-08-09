# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_pixie.py'],
    pathex=[],
    binaries=[],
    datas=[('pixie/assets', 'pixie/assets'), ('C:/msys64/ucrt64/lib/girepository-1.0', 'lib/girepository-1.0'), ('C:/msys64/ucrt64/lib/gdk-pixbuf-2.0', 'lib/gdk-pixbuf-2.0')],
    hiddenimports=['gi', 'gi._gi', 'gi.repository', 'gi.repository.GLib', 'gi.repository.GObject', 'gi.repository.Gio', 'gi.repository.GdkPixbuf', 'gi.repository.Gdk', 'gi.repository.Gtk', 'gi.repository.GdkWin32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_gi_paths.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Pixie',
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
    icon=['pixie/assets/icon.ico'],
)
