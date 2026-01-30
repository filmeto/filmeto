"""
Thread utilities for safe Qt object handling and background worker management.

This module provides utilities to handle common threading issues in Qt applications,
particularly around object lifetime management and safe callback execution.
"""

import logging
import traceback
from typing import Callable, Any, Optional, List
from PySide6.QtCore import QObject, QTimer
from app.ui.worker.worker import run_in_background, BackgroundWorker

logger = logging.getLogger(__name__)


class ThreadSafetyMixin:
    """
    A mixin class that provides thread safety utilities for Qt objects.
    
    This mixin adds methods to safely handle background operations and
    ensure object validity before executing callbacks.
    """
    
    def __init__(self):
        """Initialize thread safety features."""
        self._active_workers: List[BackgroundWorker] = []
        self._worker_callbacks = {}  # Track worker to callback mapping
    
    def is_valid_qt_object(self) -> bool:
        """
        Check if the Qt object is still valid (not destroyed).
        
        Returns:
            True if object is valid, False otherwise
        """
        try:
            from shiboken6 import isValid
            return isValid(self)
        except ImportError:
            logger.warning("shiboken6 not available, skipping object validity check")
            return True
        except Exception as e:
            logger.warning(f"Error checking object validity: {e}")
            return True  # Assume valid if we can't check
    
    def safe_run_in_background(
        self,
        task: Callable,
        on_finished: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> BackgroundWorker:
        """
        Safely run a task in the background with validity checks.
        
        Args:
            task: The task to run in background
            on_finished: Callback for successful completion (will be wrapped for safety)
            on_error: Callback for errors (will be wrapped for safety)
            *args: Arguments to pass to the task
            **kwargs: Keyword arguments to pass to the task
            
        Returns:
            BackgroundWorker instance
        """
        # Wrap callbacks to ensure object validity before execution
        wrapped_finished = self._wrap_callback(on_finished) if on_finished else None
        wrapped_error = self._wrap_callback(on_error, is_error=True) if on_error else None
        
        # Create the worker
        worker = run_in_background(
            task,
            on_finished=wrapped_finished,
            on_error=wrapped_error,
            args=args,
            kwargs=kwargs
        )
        
        # Track the worker for cleanup
        self._active_workers.append(worker)
        
        # Store callback mapping for potential later use
        self._worker_callbacks[id(worker)] = {
            'original_finished': on_finished,
            'original_error': on_error,
            'worker': worker
        }
        
        return worker
    
    def _wrap_callback(self, callback: Callable, is_error: bool = False) -> Callable:
        """
        Wrap a callback to check object validity before execution.
        
        Args:
            callback: The original callback to wrap
            is_error: Whether this is an error callback (for logging purposes)
            
        Returns:
            Wrapped callback function
        """
        def wrapped_callback(*args, **kwargs):
            # Check if the object is still valid before executing callback
            if not self.is_valid_qt_object():
                logger.warning(
                    f"Object no longer valid, skipping {'error' if is_error else 'finished'} callback"
                )
                return
            
            try:
                return callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {'error' if is_error else 'finished'} callback: {e}", exc_info=True)
                # Don't re-raise to avoid interfering with Qt's signal-slot mechanism
        
        return wrapped_callback
    
    def stop_all_workers(self):
        """Stop all active background workers."""
        for worker in self._active_workers[:]:  # Copy list to avoid modification during iteration
            try:
                if worker and worker.is_running():
                    worker.stop()
            except Exception as e:
                logger.error(f"Error stopping worker: {e}", exc_info=True)
        
        # Clear the worker lists
        self._active_workers.clear()
        self._worker_callbacks.clear()
    
    def cleanup_workers_on_deactivate(self):
        """
        Call this method when the object is deactivated to clean up workers.
        This is a convenience method that can be called from on_deactivated methods.
        """
        self.stop_all_workers()


def safe_callback_wrapper(obj: QObject, callback: Callable, is_error: bool = False) -> Callable:
    """
    Create a safe wrapper for a callback that checks object validity.
    
    Args:
        obj: The Qt object that the callback belongs to
        callback: The callback to wrap
        is_error: Whether this is an error callback
        
    Returns:
        Wrapped callback function
    """
    def wrapped_callback(*args, **kwargs):
        try:
            from shiboken6 import isValid
            if not isValid(obj):
                logger.warning(
                    f"Object no longer valid, skipping {'error' if is_error else 'finished'} callback"
                )
                return
        except ImportError:
            # If shiboken6 is not available, skip the check
            pass
        except Exception:
            # If there's any error checking validity, assume it's valid
            pass
        
        try:
            return callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {'error' if is_error else 'finished'} callback: {e}", exc_info=True)

    return wrapped_callback


def run_safe_background_task(
    obj: QObject,
    task: Callable,
    on_finished: Optional[Callable] = None,
    on_error: Optional[Callable] = None,
    *args,
    **kwargs
) -> BackgroundWorker:
    """
    Run a background task with automatic validity checking of the parent object.
    
    Args:
        obj: The Qt object that will receive callbacks
        task: The task to run in background
        on_finished: Callback for successful completion
        on_error: Callback for errors
        *args: Arguments to pass to the task
        **kwargs: Keyword arguments to pass to the task
        
    Returns:
        BackgroundWorker instance
    """
    # Wrap callbacks for safety
    wrapped_finished = safe_callback_wrapper(obj, on_finished) if on_finished else None
    wrapped_error = safe_callback_wrapper(obj, on_error, is_error=True) if on_error else None
    
    # Run the task
    return run_in_background(
        task,
        on_finished=wrapped_finished,
        on_error=wrapped_error,
        args=args,
        kwargs=kwargs
    )


class SafeWorkerManager:
    """
    A manager class to handle multiple background workers safely.
    
    This class provides a centralized way to manage background workers
    and ensure they are properly cleaned up.
    """
    
    def __init__(self):
        self._workers: List[BackgroundWorker] = []
        self._callbacks = {}
    
    def add_worker(self, worker: BackgroundWorker, finished_callback=None, error_callback=None):
        """Add a worker to be managed by this manager."""
        self._workers.append(worker)
        self._callbacks[id(worker)] = {
            'finished': finished_callback,
            'error': error_callback
        }
        
        # Connect the worker's signals to our handlers that check validity
        if finished_callback:
            worker.finished.connect(
                self._create_safe_handler(finished_callback, is_error=False)
            )
        if error_callback:
            worker.error.connect(
                self._create_safe_handler(error_callback, is_error=True)
            )
    
    def _create_safe_handler(self, callback: Callable, is_error: bool = False):
        """Create a safe handler that checks object validity."""
        def safe_handler(*args, **kwargs):
            try:
                # Check if the callback's parent object is still valid
                # This assumes the callback is a method of a QObject
                obj = callback.__self__
                from shiboken6 import isValid
                if not isValid(obj):
                    logger.warning(
                        f"Object no longer valid, skipping {'error' if is_error else 'finished'} callback"
                    )
                    return
            except AttributeError:
                # If callback doesn't have __self__, it's not a bound method
                pass
            except ImportError:
                # If shiboken6 is not available, skip the check
                pass
            except Exception:
                # If there's any error checking validity, assume it's valid
                pass
            
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {'error' if is_error else 'finished'} callback: {e}", exc_info=True)

        return safe_handler
    
    def stop_all_workers(self):
        """Stop all managed workers."""
        for worker in self._workers[:]:
            try:
                if worker.is_running():
                    worker.stop()
            except Exception as e:
                logger.error(f"Error stopping worker: {e}", exc_info=True)
        
        self._workers.clear()
        self._callbacks.clear()
    
    def get_active_count(self) -> int:
        """Get the number of currently active workers."""
        active_count = 0
        for worker in self._workers:
            try:
                if worker.is_running():
                    active_count += 1
            except:
                # If there's an error checking if worker is running, assume it's not
                continue
        return active_count