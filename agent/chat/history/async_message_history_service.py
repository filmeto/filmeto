"""Asynchronous message history service.

This module provides non-blocking message save operations by moving
file I/O to background threads, preventing UI freezing during message
persistence.

Thread Safety:
    Global singleton is protected by threading.Lock.
"""

import logging
import threading
from typing import Optional, Callable, Dict, Any
from PySide6.QtCore import QObject, Signal, QMutex, QMutexLocker

from agent.chat.agent_chat_message import AgentMessage

logger = logging.getLogger(__name__)


def _save_message_task(
    workspace_path: str,
    project_name: str,
    message: AgentMessage
) -> Dict[str, Any]:
    """Background task to save a message to storage.

    This function runs in a background thread and performs the actual
    file I/O operations (GSN allocation, file write, fsync).

    Args:
        workspace_path: Path to workspace
        project_name: Name of project
        message: The AgentMessage to save

    Returns:
        Dictionary with save result:
        - success: bool
        - workspace_path: str
        - project_name: str
        - message_id: str
        - gsn: int (0 if failed)
        - current_gsn: int (0 if failed)
        - error: str (empty if success)
    """
    try:
        from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

        # Convert message to dict (this is fast, no I/O)
        message_dict = FastMessageHistoryService._message_to_dict(message)

        # Get enhanced history and append (this does file I/O)
        from agent.chat.history.global_sequence_manager import get_enhanced_history
        enhanced_history = get_enhanced_history(workspace_path, project_name)
        success, gsn = enhanced_history.append_message(message_dict)

        if success:
            current_gsn = enhanced_history.get_current_gsn()
            return {
                "success": True,
                "workspace_path": workspace_path,
                "project_name": project_name,
                "message_id": message.message_id,
                "gsn": gsn,
                "current_gsn": current_gsn,
                "error": ""
            }
        else:
            return {
                "success": False,
                "workspace_path": workspace_path,
                "project_name": project_name,
                "message_id": message.message_id,
                "gsn": 0,
                "current_gsn": 0,
                "error": "Failed to append message to storage"
            }

    except Exception as e:
        logger.error(f"Error in background save task: {e}", exc_info=True)
        return {
            "success": False,
            "workspace_path": workspace_path,
            "project_name": project_name,
            "message_id": message.message_id if message else "",
            "gsn": 0,
            "current_gsn": 0,
            "error": str(e)
        }


class AsyncMessageHistoryService(QObject):
    """Asynchronous message save service.

    Moves file I/O operations (GSN allocation, file write, fsync) to
    background threads, preventing blocking in signal handlers.

    Qt signals are used for notifications, which automatically use
    QueuedConnection when connecting across threads.

    Usage:
        service = AsyncMessageHistoryService()

        # Connect to result signals
        service.message_saved.connect(lambda ws, proj, msg_id, gsn, curr: ...)
        service.save_error.connect(lambda msg_id, error: ...)

        # Save asynchronously (returns immediately)
        service.add_message_async(workspace, project, message)
    """

    # Qt signals - automatically use QueuedConnection across threads
    message_saved = Signal(str, str, str, int, int)  # workspace, project, message_id, gsn, current_gsn
    save_error = Signal(str, str)  # message_id, error

    def __init__(self, max_workers: int = 2, parent: Optional[QObject] = None):
        """Initialize the async service.

        Args:
            max_workers: Maximum number of concurrent save operations
            parent: Parent QObject
        """
        super().__init__(parent)

        from app.ui.worker.worker import WorkerPool
        self._worker_pool = WorkerPool(max_workers=max_workers, parent=self)
        self._mutex = QMutex()

    def add_message_async(
        self,
        workspace_path: str,
        project_name: str,
        message: AgentMessage
    ) -> None:
        """Save a message asynchronously.

        This method returns immediately. The actual file I/O happens
        in a background thread. Results are reported via signals.

        Args:
            workspace_path: Path to workspace
            project_name: Name of project
            message: The AgentMessage to save
        """
        try:
            # Submit to worker pool
            self._worker_pool.submit(
                task=_save_message_task,
                args=(workspace_path, project_name, message),
                on_finished=self._on_save_finished,
                on_error=self._on_save_error
            )
            logger.debug(f"Submitted async save for message {message.message_id}")
        except Exception as e:
            logger.error(f"Error submitting save task: {e}", exc_info=True)
            self.save_error.emit(message.message_id, str(e))

    def _on_save_finished(self, result: Dict[str, Any]) -> None:
        """Handle successful save completion.

        Called in the main thread via Qt's QueuedConnection.

        Args:
            result: Result dictionary from _save_message_task
        """
        try:
            if result.get("success"):
                # Extract workspace and project info
                workspace_path = result.get("workspace_path", "")
                project_name = result.get("project_name", "")
                message_id = result["message_id"]
                gsn = result["gsn"]
                current_gsn = result["current_gsn"]

                # Emit Qt signal with full parameters
                self.message_saved.emit(
                    workspace_path,
                    project_name,
                    message_id,
                    gsn,
                    current_gsn
                )

                # Optionally emit blinker signal for legacy compatibility
                # Only if needed - emit from main thread for safety
                try:
                    from agent.chat.history.agent_chat_history_service import message_saved as blinker_signal
                    # Use QTimer.singleShot(0, ...) to emit in next event loop iteration
                    # This ensures we're in the main thread when emitting blinker signal
                    from PySide6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: blinker_signal.send(
                        self,
                        workspace_path=workspace_path,
                        project_name=project_name,
                        message_id=message_id,
                        gsn=gsn,
                        current_gsn=current_gsn
                    ))
                except Exception as e:
                    logger.debug(f"Blinker signal emission skipped: {e}")

                logger.debug(f"Async save completed for {message_id}, GSN: {gsn}")
            else:
                error = result.get("error", "Unknown error")
                self.save_error.emit(result["message_id"], error)
                logger.warning(f"Async save failed for {result['message_id']}: {error}")
        except Exception as e:
            logger.error(f"Error in save finished callback: {e}", exc_info=True)

    def _on_save_error(self, error_msg: str, exception: Exception) -> None:
        """Handle save error.

        Args:
            error_msg: Error message string
            exception: The exception that occurred
        """
        logger.error(f"Async save error: {error_msg}", exc_info=exception)
        self.save_error.emit("", error_msg)

    def active_count(self) -> int:
        """Return number of active save operations."""
        return self._worker_pool.active_count()

    def pending_count(self) -> int:
        """Return number of pending save operations."""
        return self._worker_pool.pending_count()


# Global singleton instance and lock for thread-safe initialization
_global_async_service: Optional[AsyncMessageHistoryService] = None
_global_async_lock = threading.Lock()
_global_async_created = False


def get_async_service() -> AsyncMessageHistoryService:
    """Get the global async message history service (thread-safe).

    Uses double-checked locking pattern for efficiency.

    Returns:
        Global AsyncMessageHistoryService instance
    """
    global _global_async_service, _global_async_created

    # Fast path - no lock if already created
    if _global_async_created:
        return _global_async_service

    # Slow path - create instance with lock
    with _global_async_lock:
        if _global_async_service is None:
            _global_async_service = AsyncMessageHistoryService()
            _global_async_created = True
        return _global_async_service


def reset_global_service() -> None:
    """Reset the global service (useful for testing).

    Warning: This should only be called in test scenarios.
    """
    global _global_async_service, _global_async_created
    with _global_async_lock:
        if _global_async_service is not None:
            _global_async_service.deleteLater()
            _global_async_service = None
            _global_async_created = False
