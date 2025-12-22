"""Windows auto-update helper for 2TTS (Inno Setup installer + GitHub Releases manifest)."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Tuple

import requests

try:
    from packaging import version as packaging_version

    _HAS_PACKAGING = True
except Exception:
    _HAS_PACKAGING = False


APP_VERSION = "1.0.0"

GITHUB_REPO = "TuanTrong2290/2TTS"
UPDATE_MANIFEST_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/latest.json"


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    url: str
    sha256: str

    @staticmethod
    def from_manifest(data: dict[str, Any]) -> "UpdateInfo":
        version = str(data.get("version", "")).strip()
        url = str(data.get("url", "")).strip()
        sha256 = str(data.get("sha256", "")).strip().lower()

        if not version:
            raise ValueError("Manifest missing 'version'")
        if not url or not url.lower().startswith("https://"):
            raise ValueError("Manifest missing/invalid 'url'")
        if not sha256 or len(sha256) != 64:
            raise ValueError("Manifest missing/invalid 'sha256'")

        return UpdateInfo(version=version, url=url, sha256=sha256)


class UpdateChecker:
    def __init__(
        self,
        manifest_url: str = UPDATE_MANIFEST_URL,
        current_version: str = APP_VERSION,
    ):
        self._manifest_url = manifest_url
        self._current_version = current_version

        self._config_dir = Path.home() / ".2tts"
        self._updates_dir = self._config_dir / "updates"
        self._state_file = self._config_dir / "update_state.json"

        self._check_interval = timedelta(hours=24)

        self._last_check: Optional[datetime] = None
        self._cached_update: Optional[UpdateInfo] = None
        self._ready_update: Optional[UpdateInfo] = None
        self._ready_installer_path: Optional[Path] = None

        self._load_state()

    @property
    def current_version(self) -> str:
        return self._current_version

    @property
    def manifest_url(self) -> str:
        return self._manifest_url

    def is_newer_version(self, remote_version: str) -> bool:
        return self._is_newer(remote_version)

    def needs_check(self) -> bool:
        if not self._last_check:
            return True
        return datetime.now() - self._last_check > self._check_interval

    def get_ready_update(self) -> Optional[Tuple[UpdateInfo, Path]]:
        if not self._ready_update or not self._ready_installer_path:
            return None
        if not self._ready_installer_path.exists():
            return None
        if self._sha256_file(self._ready_installer_path) != self._ready_update.sha256:
            return None
        return self._ready_update, self._ready_installer_path

    def clear_ready_update(self, delete_file: bool = False):
        installer = self._ready_installer_path
        self._ready_update = None
        self._ready_installer_path = None
        if delete_file and installer and installer.exists():
            try:
                installer.unlink()
            except Exception:
                pass
        self._save_state()

    def check_for_updates(self, force: bool = False) -> Tuple[bool, Optional[UpdateInfo], str]:
        if not force and not self.needs_check():
            if self._cached_update and self._is_newer(self._cached_update.version):
                return True, self._cached_update, "Update available (cached)"
            return False, None, "No update available (cached)"

        try:
            update = self._fetch_manifest()
            self._last_check = datetime.now()

            if self._is_newer(update.version):
                self._cached_update = update
                self._save_state()
                return True, update, "Update available"

            self._cached_update = None
            self._save_state()
            return False, None, "You have the latest version"
        except requests.Timeout:
            return False, None, "Update check timeout"
        except requests.RequestException as e:
            return False, None, f"Update check failed: {e}"
        except Exception as e:
            return False, None, f"Update check error: {e}"

    def download_update(self, update: UpdateInfo) -> Tuple[bool, Optional[Path], str]:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._updates_dir.mkdir(parents=True, exist_ok=True)

        dest = self._updates_dir / f"2TTS-Setup-{update.version}.exe"
        if dest.exists() and self._sha256_file(dest) == update.sha256:
            self._ready_update = update
            self._ready_installer_path = dest
            self._save_state()
            return True, dest, "Update already downloaded"

        tmp = dest.with_suffix(dest.suffix + ".part")

        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass

        try:
            resp = requests.get(update.url, stream=True, timeout=60)
            resp.raise_for_status()

            hasher = hashlib.sha256()
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    hasher.update(chunk)

            actual = hasher.hexdigest().lower()
            if actual != update.sha256:
                try:
                    tmp.unlink()
                except Exception:
                    pass
                return False, None, "SHA256 mismatch for downloaded update"

            if dest.exists():
                try:
                    dest.unlink()
                except Exception:
                    pass
            tmp.replace(dest)

            self._ready_update = update
            self._ready_installer_path = dest
            self._save_state()
            return True, dest, "Update downloaded"
        except requests.Timeout:
            return False, None, "Update download timeout"
        except requests.RequestException as e:
            return False, None, f"Update download failed: {e}"
        except Exception as e:
            return False, None, f"Update download error: {e}"

    def schedule_install(
        self,
        installer_path: Path,
        *,
        relaunch_path: Optional[str] = None,
        wait_pid: Optional[int] = None,
    ) -> Tuple[bool, str]:
        if os.name != "nt":
            return False, "Auto-update is only supported on Windows"

        installer_path = Path(installer_path)
        if not installer_path.exists():
            return False, "Installer not found"

        ready = self.get_ready_update()
        if ready:
            expected = ready[0].sha256
            if self._sha256_file(installer_path) != expected:
                return False, "Installer integrity check failed (SHA256)"

        relaunch = relaunch_path or sys.executable
        pid = int(wait_pid or os.getpid())

        args = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS"

        ps = self._build_powershell_install_script(
            installer=str(installer_path),
            installer_args=args,
            wait_pid=pid,
            relaunch=str(relaunch),
        )

        try:
            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps,
                ],
                creationflags=creationflags,
                close_fds=True,
            )
            return True, "Update scheduled"
        except Exception as e:
            return False, f"Failed to start installer: {e}"

    def _fetch_manifest(self) -> UpdateInfo:
        resp = requests.get(
            self._manifest_url,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("Manifest must be a JSON object")
        return UpdateInfo.from_manifest(data)

    def _is_newer(self, remote_version: str) -> bool:
        try:
            if _HAS_PACKAGING:
                return packaging_version.parse(remote_version) > packaging_version.parse(self._current_version)
            r = [int(x) for x in remote_version.split(".")]
            c = [int(x) for x in self._current_version.split(".")]
            return r > c
        except Exception:
            return False

    def _load_state(self):
        try:
            if not self._state_file.exists():
                return
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            last_check = data.get("last_check")
            if last_check:
                self._last_check = datetime.fromisoformat(last_check)

            cached = data.get("cached_update")
            if isinstance(cached, dict):
                try:
                    self._cached_update = UpdateInfo.from_manifest(cached)
                except Exception:
                    self._cached_update = None

            ready = data.get("ready_update")
            ready_path = data.get("ready_installer_path")
            if isinstance(ready, dict) and isinstance(ready_path, str):
                try:
                    info = UpdateInfo.from_manifest(ready)
                    path = Path(ready_path)
                    if path.exists() and self._sha256_file(path) == info.sha256:
                        self._ready_update = info
                        self._ready_installer_path = path
                except Exception:
                    pass
        except Exception:
            pass

    def _save_state(self):
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            data: dict[str, Any] = {
                "last_check": self._last_check.isoformat() if self._last_check else None,
                "cached_update": {
                    "version": self._cached_update.version,
                    "url": self._cached_update.url,
                    "sha256": self._cached_update.sha256,
                }
                if self._cached_update
                else None,
                "ready_update": {
                    "version": self._ready_update.version,
                    "url": self._ready_update.url,
                    "sha256": self._ready_update.sha256,
                }
                if self._ready_update
                else None,
                "ready_installer_path": str(self._ready_installer_path) if self._ready_installer_path else None,
            }
            self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().lower()

    @staticmethod
    def _ps_quote(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"

    def _build_powershell_install_script(
        self,
        *,
        installer: str,
        installer_args: str,
        wait_pid: int,
        relaunch: str,
    ) -> str:
        installer_q = self._ps_quote(installer)
        args_q = self._ps_quote(installer_args)
        relaunch_q = self._ps_quote(relaunch)

        return (
            "$ErrorActionPreference = 'SilentlyContinue'; "
            f"$pidToWait = {wait_pid}; "
            f"$installer = {installer_q}; "
            f"$args = {args_q}; "
            f"$relaunch = {relaunch_q}; "
            "try { Wait-Process -Id $pidToWait -ErrorAction SilentlyContinue } catch {} "
            "try { Start-Process -FilePath $installer -ArgumentList $args -Wait } catch {} "
            "try { if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue } } catch {} "
            "try { Start-Process -FilePath $relaunch } catch {}"
        )


_update_checker: Optional[UpdateChecker] = None


def get_update_checker() -> UpdateChecker:
    global _update_checker
    if _update_checker is None:
        _update_checker = UpdateChecker()
    return _update_checker
