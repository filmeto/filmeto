"""
Unit tests for utils/ffmpeg_utils.py

Tests FFmpeg utility functions including:
- check_ffmpeg: Check if ffmpeg is installed
- check_ffprobe: Check if ffprobe is installed
- run_command: Run command asynchronously
- extract_first_frame: Extract first frame from video
- merge_videos: Merge multiple video files
- images_to_video: Convert images to video
- ensure_ffmpeg: Ensure ffmpeg is available
"""

import pytest
import asyncio
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from utils.ffmpeg_utils import (
    check_ffmpeg,
    check_ffprobe,
    run_command,
    extract_first_frame,
    merge_videos,
    images_to_video,
    ensure_ffmpeg,
    install_ffmpeg,
)


class TestCheckFfmpeg:
    """Tests for check_ffmpeg function."""

    @patch("subprocess.run")
    def test_check_ffmpeg_returns_true_when_available(self, mock_run):
        """check_ffmpeg returns True when ffmpeg is available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = check_ffmpeg()
        assert result is True

    @patch("subprocess.run")
    def test_check_ffmpeg_returns_false_on_nonzero_return(self, mock_run):
        """check_ffmpeg returns False when ffmpeg returns non-zero."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = check_ffmpeg()
        assert result is False

    @patch("subprocess.run")
    def test_check_ffmpeg_returns_false_on_file_not_found(self, mock_run):
        """check_ffmpeg returns False when ffmpeg not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = check_ffmpeg()
        assert result is False


class TestCheckFfprobe:
    """Tests for check_ffprobe function."""

    @patch("subprocess.run")
    def test_check_ffprobe_returns_true_when_available(self, mock_run):
        """check_ffprobe returns True when ffprobe is available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = check_ffprobe()
        assert result is True

    @patch("subprocess.run")
    def test_check_ffprobe_returns_false_on_file_not_found(self, mock_run):
        """check_ffprobe returns False when ffprobe not installed."""
        mock_run.side_effect = FileNotFoundError()

        result = check_ffprobe()
        assert result is False


class TestRunCommand:
    """Tests for run_command async function."""

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec")
    async def test_run_command_returns_completed_process(self, mock_create_subprocess):
        """run_command returns CompletedProcess with results."""
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(b"output", b"error"))
        mock_process.returncode = 0
        mock_create_subprocess.return_value = mock_process

        with patch("platform.system", return_value="Linux"):
            result = await run_command(["ffmpeg", "-version"])

            assert result.returncode == 0
            assert result.stdout == b"output"

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_run_command_fallback_on_windows(self, mock_run):
        """run_command uses subprocess.run on Windows."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = b"output"
        mock_run.return_value = mock_result

        with patch("platform.system", return_value="Windows"):
            result = await run_command(["ffmpeg", "-version"])

            mock_run.assert_called_once()


class TestExtractFirstFrame:
    """Tests for extract_first_frame function."""

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=False)
    async def test_extract_first_frame_returns_false_without_ffmpeg(self, mock_check):
        """extract_first_frame returns False when ffmpeg not available."""
        result = await extract_first_frame("video.mp4", "frame.png")
        assert result is False

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("utils.ffmpeg_utils.run_command")
    async def test_extract_first_frame_success(self, mock_run, mock_check):
        """extract_first_frame returns True on successful extraction."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = await extract_first_frame("/tmp/video.mp4", "/tmp/frame.png")
        assert result is True

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("utils.ffmpeg_utils.run_command")
    async def test_extract_first_frame_failure(self, mock_run, mock_check):
        """extract_first_frame returns False on extraction failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = b"error"
        mock_run.return_value = mock_result

        result = await extract_first_frame("/tmp/video.mp4", "/tmp/frame.png")
        assert result is False


class TestMergeVideos:
    """Tests for merge_videos function."""

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=False)
    async def test_merge_videos_returns_false_without_ffmpeg(self, mock_check):
        """merge_videos returns False when ffmpeg not available."""
        result = await merge_videos(["v1.mp4"], "output.mp4")
        assert result is False

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    async def test_merge_videos_returns_false_empty_list(self, mock_check):
        """merge_videos returns False when video list is empty."""
        result = await merge_videos([], "output.mp4")
        assert result is False

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("os.path.exists", return_value=False)
    async def test_merge_videos_returns_false_missing_file(self, mock_exists, mock_check):
        """merge_videos returns False when video file doesn't exist."""
        result = await merge_videos(["missing.mp4"], "output.mp4")
        assert result is False


class TestImagesToVideo:
    """Tests for images_to_video function."""

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=False)
    async def test_images_to_video_returns_false_without_ffmpeg(self, mock_check):
        """images_to_video returns False when ffmpeg not available."""
        result = await images_to_video(["img1.png"], "output.mp4")
        assert result is False

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    async def test_images_to_video_returns_false_empty_list(self, mock_check):
        """images_to_video returns False when image list is empty."""
        result = await images_to_video([], "output.mp4")
        assert result is False

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("os.path.exists", return_value=False)
    async def test_images_to_video_returns_false_missing_file(self, mock_exists, mock_check):
        """images_to_video returns False when image file doesn't exist."""
        result = await images_to_video(["missing.png"], "output.mp4")
        assert result is False


class TestEnsureFfmpeg:
    """Tests for ensure_ffmpeg function."""

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("utils.ffmpeg_utils.check_ffprobe", return_value=True)
    async def test_ensure_ffmpeg_returns_true_when_both_available(self, mock_ffprobe, mock_ffmpeg):
        """ensure_ffmpeg returns True when both ffmpeg and ffprobe available."""
        result = await ensure_ffmpeg()
        assert result is True

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=True)
    @patch("utils.ffmpeg_utils.check_ffprobe", return_value=False)
    async def test_ensure_ffmpeg_returns_true_ffmpeg_only(self, mock_ffprobe, mock_ffmpeg):
        """ensure_ffmpeg returns True when only ffmpeg available."""
        result = await ensure_ffmpeg()
        assert result is True

    @pytest.mark.asyncio
    @patch("utils.ffmpeg_utils.check_ffmpeg", return_value=False)
    @patch("utils.ffmpeg_utils.install_ffmpeg")
    async def test_ensure_ffmpeg_attempts_install(self, mock_install, mock_check):
        """ensure_ffmpeg attempts installation when ffmpeg not available."""
        mock_install.return_value = False

        result = await ensure_ffmpeg()
        mock_install.assert_called_once()


class TestInstallFfmpeg:
    """Tests for install_ffmpeg function."""

    @pytest.mark.asyncio
    @patch("platform.system", return_value="Windows")
    async def test_install_ffmpeg_windows_returns_false(self, mock_system):
        """install_ffmpeg returns False on Windows (manual install needed)."""
        result = await install_ffmpeg()
        assert result is False

    @pytest.mark.asyncio
    @patch("platform.system", return_value="Linux")
    @patch("utils.ffmpeg_utils.run_command")
    async def test_install_ffmpeg_linux_attempts_package_manager(self, mock_run, mock_system):
        """install_ffmpeg tries package managers on Linux."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = await install_ffmpeg()
        # Should try some package manager check
        assert mock_run.called