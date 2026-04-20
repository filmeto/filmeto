"""
Tests for ShotTaskExecutor and ShotTaskManager.

Tests the independent task queue for storyboard keyframe generation.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from pathlib import Path


class TestShotTaskManager:
    """Tests for ShotTaskManager."""

    def test_shot_task_manager_init(self):
        """Test ShotTaskManager initialization."""
        from app.data.story_board.shot_task_manager import ShotTaskManager
        from app.data.story_board.story_board_shot import StoryBoardShot

        # Create mock shot
        shot = StoryBoardShot(
            scene_id="scene_01",
            shot_id="01",
            title="Test Shot",
        )

        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "scene_01", "01")
            os.makedirs(shot_dir, exist_ok=True)

            executor_mock = Mock()
            manager = ShotTaskManager(shot, shot_dir, executor_mock)

            # Verify tasks_path is correct
            assert manager.tasks_path == os.path.join(shot_dir, "keyframes")
            assert os.path.exists(manager.tasks_path)

    def test_shot_task_manager_task_index(self):
        """Test task index tracking."""
        from app.data.story_board.shot_task_manager import ShotTaskManager
        from app.data.story_board.story_board_shot import StoryBoardShot

        shot = StoryBoardShot(scene_id="scene_01", shot_id="01")

        with tempfile.TemporaryDirectory() as tmpdir:
            shot_dir = os.path.join(tmpdir, "scene_01", "01")
            os.makedirs(shot_dir, exist_ok=True)

            executor_mock = Mock()
            manager = ShotTaskManager(shot, shot_dir, executor_mock)

            # Test index progression
            assert manager._get_next_task_index() == 0
            manager._increment_task_index()
            assert manager._get_next_task_index() == 1


class TestTaskShotMethods:
    """Tests for Task shot-related methods."""

    def test_task_is_shot_task_detection(self):
        """Test is_shot_task() detection - only explicit flag counts."""
        from app.data.task import Task

        # Create mock managers
        storage_mock = Mock()
        progress_mock = Mock()

        # Shot task options (MUST have explicit is_shot_task=True)
        shot_options = {
            "tool": "text2image",
            "shot_id": "01",
            "scene_id": "scene_01",
            "is_shot_task": True,  # Explicit flag required
        }

        # Timeline task options
        timeline_options = {
            "tool": "text2image",
            "timeline_index": 0,
            "timeline_item_id": 0,
        }

        # Options with shot_id but NO explicit flag (should NOT be shot task)
        shot_id_only_options = {
            "tool": "text2image",
            "shot_id": "01",
            "scene_id": "scene_01",
            # NO is_shot_task flag
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            # Shot task (explicit flag)
            shot_task_path = os.path.join(tmpdir, "shot_task")
            os.makedirs(shot_task_path)
            shot_task = Task(storage_mock, progress_mock, shot_task_path, shot_options)

            # Timeline task
            timeline_task_path = os.path.join(tmpdir, "timeline_task")
            os.makedirs(timeline_task_path)
            timeline_task = Task(storage_mock, progress_mock, timeline_task_path, timeline_options)

            # Shot_id only (no explicit flag)
            shot_id_only_path = os.path.join(tmpdir, "shot_id_only")
            os.makedirs(shot_id_only_path)
            shot_id_only_task = Task(storage_mock, progress_mock, shot_id_only_path, shot_id_only_options)

            # Verify detection
            assert shot_task.is_shot_task() == True  # Only explicit flag counts
            assert timeline_task.is_shot_task() == False
            assert shot_id_only_task.is_shot_task() == False  # shot_id alone does NOT make it shot task

    def test_task_shot_id_methods(self):
        """Test get_shot_id() and get_scene_id() methods."""
        from app.data.task import Task

        storage_mock = Mock()
        progress_mock = Mock()

        options = {
            "tool": "text2image",
            "shot_id": "02",
            "scene_id": "scene_02",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = os.path.join(tmpdir, "test_task")
            os.makedirs(task_path)
            task = Task(storage_mock, progress_mock, task_path, options)

            assert task.get_shot_id() == "02"
            assert task.get_scene_id() == "scene_02"


class TestTaskResultShotMethods:
    """Tests for TaskResult shot-related methods."""

    def test_task_result_shot_methods(self):
        """Test TaskResult shot methods."""
        from app.data.task import Task, TaskResult
        from app.spi.model import BaseModelResult

        # Create mocks
        storage_mock = Mock()
        progress_mock = Mock()
        result_mock = Mock(spec=BaseModelResult)
        result_mock.get_image_path.return_value = "/path/to/image.png"

        options = {
            "tool": "text2image",
            "shot_id": "03",
            "scene_id": "scene_03",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            task_path = os.path.join(tmpdir, "test_task")
            os.makedirs(task_path)
            task = Task(storage_mock, progress_mock, task_path, options)

            task_result = TaskResult(task, result_mock)

            assert task_result.get_shot_id() == "03"
            assert task_result.get_scene_id() == "scene_03"
            assert task_result.is_shot_result() == False  # No explicit is_shot_task flag
            assert task_result.get_image_path() == "/path/to/image.png"


class TestShotTaskExecutor:
    """Tests for ShotTaskExecutor."""

    def test_executor_init(self):
        """Test ShotTaskExecutor initialization."""
        from app.data.story_board.shot_task_executor import ShotTaskExecutor

        manager_mock = Mock()
        executor = ShotTaskExecutor(manager_mock)

        assert executor.manager == manager_mock
        assert executor.create_queue is not None
        assert executor.execute_queue is not None

    def test_executor_signal_connection(self):
        """Test signal connection methods."""
        from app.data.story_board.shot_task_executor import ShotTaskExecutor

        manager_mock = Mock()
        executor = ShotTaskExecutor(manager_mock)

        # Test signal connections
        create_handler = Mock()
        progress_handler = Mock()
        finished_handler = Mock()

        executor.connect_task_create(create_handler)
        executor.connect_task_progress(progress_handler)
        executor.connect_task_finished(finished_handler)

        # Verify connections exist (blinker signals)
        assert len(executor.task_create.receivers) > 0
        assert len(executor.task_progress.receivers) > 0
        assert len(executor.task_finished.receivers) > 0

    def test_executor_clear_cache(self):
        """Test clear_shot_task_managers."""
        from app.data.story_board.shot_task_executor import ShotTaskExecutor

        manager_mock = Mock()
        executor = ShotTaskExecutor(manager_mock)

        # Add some cached managers
        executor._shot_task_managers["scene_01/01"] = Mock()
        executor._shot_task_managers["scene_01/02"] = Mock()

        executor.clear_shot_task_managers()

        assert len(executor._shot_task_managers) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])