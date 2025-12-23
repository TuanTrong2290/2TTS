#!/usr/bin/env python3
"""Build script to package Python backend as a sidecar for Tauri"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


def main():
    root_dir = Path(__file__).parent.parent.parent
    backend_dir = root_dir / "backend"
    app_dir = root_dir / "app"
    sidecar_dir = root_dir / "desktop" / "src-tauri" / "sidecar"
    
    # Create sidecar directory
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    
    print("Building Python backend sidecar...")
    
    # Create PyInstaller spec for backend
    spec_content = f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{backend_dir / "main.py"}'],
    pathex=['{backend_dir}', '{app_dir}'],
    binaries=[],
    datas=[
        ('{app_dir / "resources"}', 'resources'),
    ],
    hiddenimports=[
        'core.config',
        'core.models',
        'services.elevenlabs',
        'services.audio',
        'services.processing',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'PyQt6',
        'tkinter',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='2tts-backend',
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
'''
    
    spec_file = backend_dir / "backend.spec"
    with open(spec_file, "w") as f:
        f.write(spec_content)
    
    # Run PyInstaller
    try:
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", str(spec_file)],
            cwd=str(backend_dir),
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed: {e}")
        return 1
    
    # Copy built executable to sidecar directory
    dist_dir = backend_dir / "dist"
    if sys.platform == "win32":
        exe_name = "2tts-backend.exe"
    else:
        exe_name = "2tts-backend"
    
    src_exe = dist_dir / exe_name
    dst_exe = sidecar_dir / exe_name
    
    if src_exe.exists():
        shutil.copy2(src_exe, dst_exe)
        print(f"Sidecar built successfully: {dst_exe}")
    else:
        print(f"Error: Built executable not found at {src_exe}")
        return 1
    
    # Cleanup
    shutil.rmtree(backend_dir / "build", ignore_errors=True)
    spec_file.unlink(missing_ok=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
