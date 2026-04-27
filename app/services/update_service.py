import asyncio
import logging
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

import aiohttp

from app.version import APP_NAME, APP_VERSION, UPDATE_URL

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    """Information about an available update."""
    version: str
    release_notes: str
    force_update: bool
    download_url: str
    checksum: Optional[str] = None


def _parse_version(version_str: str) -> tuple:
    """Parse version string into comparable tuple. e.g. '1.2.3' -> (1, 2, 3)"""
    try:
        parts = []
        for p in version_str.strip().split("."):
            # Strip any non-numeric suffixes (e.g., "1.2.3-beta" -> (1, 2, 3))
            numeric = ""
            for ch in p:
                if ch.isdigit():
                    numeric += ch
                else:
                    break
            parts.append(int(numeric) if numeric else 0)
        return tuple(parts)
    except (ValueError, AttributeError):
        return (0,)


def _has_update_available(current: str, latest: str) -> bool:
    """Return True if latest version is newer than current."""
    return _parse_version(latest) > _parse_version(current)


def _get_platform_key() -> str:
    """Return the platform key for download URL selection."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    return "macos"  # default


class UpdateService:
    """Service for checking, downloading, and installing application updates."""

    def __init__(self):
        self.current_version = APP_VERSION
        self._update_info: Optional[UpdateInfo] = None

    async def check_for_update(self) -> Optional[UpdateInfo]:
        """
        Check for updates from the configured update URL.
        Returns UpdateInfo if a newer version is available, None otherwise.
        """
        try:
            logger.info("Checking for updates at %s ...", UPDATE_URL)
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(UPDATE_URL) as resp:
                    if resp.status != 200:
                        logger.warning("Update check HTTP %d", resp.status)
                        return None
                    data = await resp.json()

            latest_version = data.get("version", "")
            release_notes = data.get("release_notes", "")
            force_update = data.get("force_update", False)
            downloads = data.get("downloads", {})

            platform_key = _get_platform_key()
            download_url = downloads.get(platform_key) or downloads.get("macos", "")

            if not download_url:
                logger.warning("No download URL for platform '%s'", platform_key)
                return None

            if not _has_update_available(self.current_version, latest_version):
                logger.info("Already on latest version %s", self.current_version)
                return None

            self._update_info = UpdateInfo(
                version=latest_version,
                release_notes=release_notes,
                force_update=force_update,
                download_url=download_url,
                checksum=data.get("checksum"),
            )
            logger.info(
                "Update available: %s -> %s", self.current_version, latest_version
            )
            return self._update_info

        except asyncio.TimeoutError:
            logger.warning("Update check timed out")
        except aiohttp.ClientError as e:
            logger.warning("Update check network error: %s", e)
        except Exception as e:
            logger.warning("Update check failed: %s", e)
        return None

    async def download_update(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        cancel_flag: Optional[object] = None,
    ) -> Optional[str]:
        """
        Download the update package.
        progress_callback(downloaded_bytes, total_bytes) is called periodically.
        cancel_flag: a simple object with an .is_set bool attribute; set it to cancel.
        Returns the path to the downloaded file, or None on failure/cancel.
        """
        if not self._update_info:
            logger.error("No update info available")
            return None

        url = self._update_info.download_url
        filename = os.path.basename(urlparse(url).path)
        if not filename or filename.endswith("/"):
            filename = f"{APP_NAME}_update.bin"

        dest_dir = tempfile.gettempdir()
        filepath = os.path.join(dest_dir, filename)

        logger.info("Downloading update from %s to %s", url, filepath)

        try:
            timeout = aiohttp.ClientTimeout(total=3600, connect=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error("Download HTTP %d", resp.status)
                        return None

                    total_size = int(resp.headers.get("content-length", 0))
                    downloaded = 0

                    with open(filepath, "wb") as f:
                        async for chunk in resp.content.iter_chunked(64 * 1024):
                            if cancel_flag is not None and getattr(cancel_flag, "is_set", False):
                                logger.info("Download cancelled")
                                if os.path.exists(filepath):
                                    os.remove(filepath)
                                return None
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)

            logger.info("Update downloaded to %s", filepath)
            return filepath

        except asyncio.CancelledError:
            logger.info("Download cancelled")
            if os.path.exists(filepath):
                os.remove(filepath)
            return None
        except Exception as e:
            logger.error("Download failed: %s", e)
            return None

    def install_update(self, filepath: str) -> bool:
        """
        Install the downloaded update package.
        Platform-specific behavior:
          - macOS: mount .dmg, copy .app to /Applications, unmount
          - Windows: run .exe installer
          - Linux: handle .AppImage or .deb
        Returns True if installation was initiated successfully.
        """
        try:
            system = platform.system().lower()
            ext = Path(filepath).suffix.lower()

            if system == "darwin":
                return self._install_macos(filepath)
            elif system == "windows":
                return self._install_windows(filepath)
            elif system == "linux":
                return self._install_linux(filepath)
            else:
                logger.warning("Unsupported platform: %s", system)
                return False

        except Exception as e:
            logger.error("Installation failed: %s", e)
            return False

    def _install_macos(self, filepath: str) -> bool:
        """macOS: mount .dmg, copy .app, unmount, then launch new version."""
        try:
            # Mount the DMG
            result = subprocess.run(
                ["hdiutil", "attach", "-nobrowse", "-noautoopen", filepath],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("hdiutil attach failed: %s", result.stderr)
                return False

            # Find the mounted volume
            output = result.stdout.strip()
            mount_point = None
            for line in output.split("\n"):
                parts = line.strip().split("\t")
                if len(parts) >= 3 and "/Volumes/" in parts[-1]:
                    mount_point = parts[-1]
                    break

            if not mount_point or not os.path.exists(mount_point):
                logger.error("Could not find mount point in: %s", output)
                return False

            logger.info("Mounted at: %s", mount_point)

            # Find and copy the .app bundle
            app_name = f"{APP_NAME}.app"
            # Search for the .app in the mounted volume
            app_source = None
            for root, dirs, files in os.walk(mount_point):
                for d in dirs:
                    if d == app_name:
                        app_source = os.path.join(root, d)
                        break
                if app_source:
                    break

            if not app_source:
                logger.error("Could not find %s in mounted volume", app_name)
                return False

            # Copy to /Applications using rsync or cp
            dest = f"/Applications/{app_name}"
            result = subprocess.run(
                ["cp", "-R", "-f", app_source, "/Applications/"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error("cp failed: %s", result.stderr)
                return False

            # Unmount
            subprocess.run(
                ["hdiutil", "detach", mount_point, "-quiet"],
                capture_output=True, timeout=15,
            )

            # Launch the new version
            self._launch_app(dest)

            # Exit current app
            self._exit_current_app()
            return True

        except subprocess.TimeoutExpired as e:
            logger.error("macOS install timeout: %s", e)
            return False
        except Exception as e:
            logger.error("macOS install failed: %s", e)
            return False

    def _install_windows(self, filepath: str) -> bool:
        """Windows: run the installer."""
        try:
            subprocess.Popen(
                [filepath, "/SILENT"],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self._exit_current_app()
            return True
        except Exception as e:
            logger.error("Windows install failed: %s", e)
            return False

    def _install_linux(self, filepath: str) -> bool:
        """Linux: handle .AppImage or .deb."""
        try:
            ext = Path(filepath).suffix.lower()
            if ext == ".appimage":
                os.chmod(filepath, 0o755)
                subprocess.Popen([filepath])
                self._exit_current_app()
                return True
            elif ext == ".deb":
                subprocess.Popen(
                    ["pkexec", "dpkg", "-i", filepath],
                )
                self._exit_current_app()
                return True
            else:
                logger.warning("Unknown Linux package format: %s", ext)
                return False
        except Exception as e:
            logger.error("Linux install failed: %s", e)
            return False

    @staticmethod
    def _launch_app(app_path: str):
        """Launch the updated application."""
        try:
            subprocess.Popen(["open", app_path])
        except Exception as e:
            logger.warning("Could not auto-launch updated app: %s", e)

    @staticmethod
    def _exit_current_app():
        """Exit the current application process. For macOS, quit cleanly."""
        try:
            if platform.system() == "Darwin":
                subprocess.Popen(["osascript", "-e", 'tell application "System Events" to quit'])
        except Exception as e:
            logger.warning("Could not exit current app: %s", e)
