# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for 2TTS application"""

import sys
from pathlib import Path

block_cipher = None

# Get the app directory
app_dir = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(app_dir)],
    binaries=[],
    datas=[
        ('resources/icon.ico', 'resources'),
        ('resources/icon.png', 'resources'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtMultimedia',
        'requests',
        'aiohttp',
        'langdetect',
        'pysrt',
        'docx',
        'pydub',
        'socks',
        'supabase',
        'packaging',
        'packaging.version',
        'concurrent.futures',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='2TTS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Enable console for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='2TTS',
)
