"""
Build and Release Script for 2TTS
Automates: PyInstaller build -> Inno Setup installer -> latest.json manifest
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


GITHUB_REPO = "TuanTrong2290/2TTS"
APP_NAME = "2TTS"


def get_version_from_updater() -> str:
    """Extract current version from updater.py"""
    updater_path = Path(__file__).parent.parent / "services" / "updater.py"
    if updater_path.exists():
        content = updater_path.read_text(encoding="utf-8")
        match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return "1.0.0"


def set_version(version: str) -> bool:
    """Update version in all relevant files"""
    app_dir = Path(__file__).parent.parent
    
    # Update updater.py
    updater_path = app_dir / "services" / "updater.py"
    if updater_path.exists():
        content = updater_path.read_text(encoding="utf-8")
        content = re.sub(
            r'APP_VERSION\s*=\s*["\'][^"\']+["\']',
            f'APP_VERSION = "{version}"',
            content
        )
        updater_path.write_text(content, encoding="utf-8")
        print(f"  Updated: services/updater.py")
    
    # Update 2TTS.iss
    iss_path = app_dir / "installer" / "2TTS.iss"
    if iss_path.exists():
        content = iss_path.read_text(encoding="utf-8")
        content = re.sub(
            r'#define AppVersion "[^"]+"',
            f'#define AppVersion "{version}"',
            content
        )
        content = re.sub(
            r'#define AppVersionInfo "[^"]+"',
            f'#define AppVersionInfo "{version}.0"',
            content
        )
        iss_path.write_text(content, encoding="utf-8")
        print(f"  Updated: installer/2TTS.iss")
    
    return True


def sha256_file(path: Path) -> str:
    """Calculate SHA256 hash of a file"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def find_inno_setup() -> Optional[str]:
    """Find Inno Setup compiler"""
    paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def run_command(cmd: list, cwd: Optional[Path] = None) -> bool:
    """Run a command and return success status"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def build_app(app_dir: Path) -> bool:
    """Build the app with PyInstaller"""
    print("\n" + "=" * 50)
    print("Step 1: Building application with PyInstaller")
    print("=" * 50)
    
    build_dir = app_dir / "build"
    dist_dir = app_dir / "dist"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    return run_command(
        [sys.executable, "-m", "PyInstaller", "2tts.spec", "--clean"],
        cwd=app_dir
    )


def build_installer(app_dir: Path, version: str) -> Optional[Path]:
    """Build installer with Inno Setup"""
    print("\n" + "=" * 50)
    print("Step 2: Building installer with Inno Setup")
    print("=" * 50)
    
    iscc = find_inno_setup()
    if not iscc:
        print("ERROR: Inno Setup not found!")
        print("Please install Inno Setup 6 from: https://jrsoftware.org/isinfo.php")
        return None
    
    dist_installer = app_dir / "dist_installer"
    if dist_installer.exists():
        shutil.rmtree(dist_installer)
    dist_installer.mkdir(exist_ok=True)
    
    iss_file = app_dir / "installer" / "2TTS.iss"
    if not run_command([iscc, str(iss_file)], cwd=app_dir):
        return None
    
    installer_path = dist_installer / f"{APP_NAME}-Setup-{version}.exe"
    if installer_path.exists():
        return installer_path
    
    for f in dist_installer.glob("*.exe"):
        return f
    
    return None


def create_manifest(installer_path: Path, version: str, output_dir: Path) -> Path:
    """Create latest.json manifest for auto-updater"""
    print("\n" + "=" * 50)
    print("Step 3: Creating update manifest (latest.json)")
    print("=" * 50)
    
    sha256 = sha256_file(installer_path)
    
    manifest = {
        "version": version,
        "url": f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{installer_path.name}",
        "sha256": sha256
    }
    
    manifest_path = output_dir / "latest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    
    print(f"  Version: {version}")
    print(f"  SHA256:  {sha256}")
    print(f"  URL:     {manifest['url']}")
    print(f"  Saved:   {manifest_path}")
    
    return manifest_path


def create_github_release(version: str, installer_path: Path, manifest_path: Path) -> bool:
    """Create GitHub release using gh CLI"""
    print("\n" + "=" * 50)
    print("Step 4: Creating GitHub Release")
    print("=" * 50)
    
    # Check if gh is available
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True)
        if result.returncode != 0:
            raise FileNotFoundError()
    except FileNotFoundError:
        print("WARNING: GitHub CLI (gh) not installed")
        print("Install from: https://cli.github.com/")
        print("\nManual release instructions:")
        print(f"  1. Go to: https://github.com/{GITHUB_REPO}/releases/new")
        print(f"  2. Tag: v{version}")
        print(f"  3. Upload: {installer_path}")
        print(f"  4. Upload: {manifest_path}")
        return False
    
    # Create release
    cmd = [
        "gh", "release", "create",
        f"v{version}",
        str(installer_path),
        str(manifest_path),
        "--title", f"v{version}",
        "--notes", f"Release v{version}"
    ]
    
    print(f"Creating release v{version}...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"\nRelease created: https://github.com/{GITHUB_REPO}/releases/tag/v{version}")
        return True
    else:
        print("\nERROR: Failed to create release")
        print("You may need to run: gh auth login")
        return False


def main():
    app_dir = Path(__file__).parent.parent.resolve()
    os.chdir(app_dir)
    
    # Get version from command line or current files
    if len(sys.argv) > 1:
        version = sys.argv[1]
        print(f"Setting version to {version}...")
        set_version(version)
    else:
        version = get_version_from_updater()
    
    print(f"\nBuilding {APP_NAME} v{version}")
    
    if not build_app(app_dir):
        print("\nERROR: PyInstaller build failed!")
        sys.exit(1)
    
    installer_path = build_installer(app_dir, version)
    if not installer_path:
        print("\nERROR: Installer build failed!")
        sys.exit(1)
    
    manifest_path = create_manifest(
        installer_path, 
        version, 
        installer_path.parent
    )
    
    create_github_release(version, installer_path, manifest_path)
    
    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
