# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['../app'],
    binaries=[],
    datas=[],
    hiddenimports=['core', 'core.config', 'core.models', 'services', 'services.elevenlabs', 'services.file_import', 'services.audio', 'ipc', 'ipc.server', 'ipc.handlers', 'ipc.types', 'requests', 'pysrt', 'docx', 'langdetect', 'pydub'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5', 'tkinter', 'matplotlib', 'numpy', 'PIL', 'supabase'],
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
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
