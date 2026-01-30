"""Generic background worker component using QThread + QObject pattern.

This module provides a non-blocking way to execute tasks in background threads
without freezing the main UI thread. It uses the recommended "move object to thread"
pattern instead of subclassing QThread.

Usage:
    # Create a worker for a specific task
    worker = BackgroundWorker()
    worker.set_task(my_function, arg1, arg2, kwarg1=value)
    worker.finished.connect(on_result)
    worker.error.connect(on_error)
    worker.start()

    # Or use the convenience function
    run_in_background(my_function, on_finished=callback, args=(arg1,), kwargs={'key': val})
"""

import logging
import traceback
from typing import Any, Callable, Optional, Tuple, Dict, List
from PySide6.QtCore import QObject, QThread, Signal, Slot

logger = logging.getLogger(__name__)


class TaskExecutor(QObject):
    """Worker object that executes tasks in a background thread.
    
    This class is moved to a QThread and executes tasks when triggered.
    All signal emissions are thread-safe due to Qt's automatic queued connections.
    """
    
    # Signals for communicating results back to the main thread
    finished = Signal(object)       # Task completed successfully with result
    error = Signal(str, object)     # Task failed with error message and exception
    progress = Signal(int, str)     # Progress update (percent, message)
    started = Signal()              # Task execution started
    
    def __init__(self):
        super().__init__()
        self._task: Optional[Callable] = None
        self._args: Tuple = ()
        self._kwargs: Dict = {}
    
    def set_task(self, task: Callable, *args, **kwargs):
        """Set the task to be executed.
        
        Args:
            task: Callable to execute
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task
        """
        self._task = task
        self._args = args
        self._kwargs = kwargs
    
    @Slot()
    def execute(self):
        """Execute the configured task.
        
        This method runs in the background thread.
        """
        if self._task is None:
            self.error.emit("No task configured", None)
            return
        
        try:
            self.started.emit()
            logger.debug(f"Executing task: {self._task.__name__ if hasattr(self._task, '__name__') else self._task}")
            
            # Execute the task
            result = self._task(*self._args, **self._kwargs)
            
            # Emit result
            self.finished.emit(result)
            logger.debug(f"Task completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task execution failed: {error_msg}", exc_info=True)
            self.error.emit(error_msg, e)
    
    def report_progress(self, percent: int, message: str = ""):
        """Report progress from within the task.
        
        Call this from your task function to report progress.
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
        """
        self.progress.emit(percent, message)


class BackgroundWorker(QObject):
    """High-level wrapper for executing tasks in a background thread.
    
    This class manages the QThread lifecycle and provides a simple API
    for running tasks without blocking the UI.
    
    Example:
        worker = BackgroundWorker()
        worker.set_task(load_image, "path/to/image.png")
        worker.finished.connect(lambda result: logger.info(f"Loaded: {result}"))
        worker.error.connect(lambda msg, e: logger.error(f"Error: {msg}"))
        worker.start()
    """
    
    # Forward signals from TaskExecutor
    finished = Signal(object)
    error = Signal(str, object)
    progress = Signal(int, str)
    started = Signal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._thread: Optional[QThread] = None
        self._executor: Optional[TaskExecutor] = None
        self._auto_cleanup = True
    
    def set_task(self, task: Callable, *args, **kwargs):
        """Set the task to be executed.
        
        Args:
            task: Callable to execute in background
            *args: Positional arguments for the task
            **kwargs: Keyword arguments for the task
        """
        self._setup_thread()
        self._executor.set_task(task, *args, **kwargs)
    
    def _setup_thread(self):
        """Initialize thread and executor if not already done."""
        if self._thread is not None:
            return
        
        # Create thread and executor
        self._thread = QThread()
        self._executor = TaskExecutor()
        
        # Move executor to thread
        self._executor.moveToThread(self._thread)
        
        # Connect signals
        self._executor.finished.connect(self._on_finished)
        self._executor.error.connect(self._on_error)
        self._executor.progress.connect(self.progress)
        self._executor.started.connect(self.started)
        
        # Auto-cleanup on finish if enabled
        if self._auto_cleanup:
            self._executor.finished.connect(self._cleanup)
            self._executor.error.connect(self._cleanup)
    
    def start(self):
        """Start the background task."""
        if self._thread is None or self._executor is None:
            logger.error("No task configured. Call set_task() first.")
            return
        
        if self._thread.isRunning():
            logger.warning("Worker is already running")
            return
        
        # Start thread
        self._thread.start()
        
        # Trigger task execution (queued connection ensures it runs in thread)
        # Use QMetaObject.invokeMethod for thread-safe invocation
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(self._executor, "execute", Qt.QueuedConnection)
    
    def _on_finished(self, result):
        """Handle task completion."""
        self.finished.emit(result)
    
    def _on_error(self, msg, exception):
        """Handle task error."""
        self.error.emit(msg, exception)
    
    def _cleanup(self, *args):
        """Clean up thread resources safely."""
        if self._thread is not None:
            # Disconnect all signals first to prevent any callbacks during cleanup
            try:
                if self._executor is not None:
                    self._executor.finished.disconnect()
                    self._executor.error.disconnect()
                    self._executor.progress.disconnect()
                    self._executor.started.disconnect()
            except Exception:
                pass  # Ignore errors if signals are already disconnected
            
            # Quit the thread and wait for it to finish
            self._thread.quit()
            # Wait with timeout to avoid blocking indefinitely
            if not self._thread.wait(3000):  # 3 second timeout
                logger.warning(f"Thread did not finish in time, terminating forcefully")
                self._thread.terminate()
                self._thread.wait(1000)  # Wait 1 more second after terminate
            
            # Schedule thread deletion
            self._thread.deleteLater()
            self._thread = None
        
        if self._executor is not None:
            self._executor.deleteLater()
            self._executor = None
    
    def stop(self):
        """Stop the worker and clean up resources."""
        self._cleanup()
    
    def is_running(self) -> bool:
        """Check if the worker is currently running."""
        return self._thread is not None and self._thread.isRunning()
    
    def set_auto_cleanup(self, enabled: bool):
        """Set whether to automatically clean up after task completion.
        
        Args:
            enabled: If True, thread resources are freed after task completes
        """
        self._auto_cleanup = enabled
    
    def get_executor(self) -> Optional[TaskExecutor]:
        """Get the TaskExecutor for direct progress reporting.
        
        Returns:
            TaskExecutor instance or None if not set up
        """
        return self._executor


class WorkerPool(QObject):
    """Manages multiple background workers for concurrent task execution.
    
    Use this when you need to run multiple independent tasks concurrently.
    
    Example:
        pool = WorkerPool(max_workers=4)
        pool.submit(task1, callback1)
        pool.submit(task2, callback2)
    """
    
    all_finished = Signal()  # Emitted when all tasks complete
    
    def __init__(self, max_workers: int = 4, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._max_workers = max_workers
        self._active_workers: List[BackgroundWorker] = []
        self._pending_tasks: List[Tuple[Callable, Tuple, Dict, Optional[Callable], Optional[Callable]]] = []
    
    def submit(
        self,
        task: Callable,
        on_finished: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None,
        args: Tuple = (),
        kwargs: Optional[Dict] = None
    ):
        """Submit a task for background execution.
        
        Args:
            task: Callable to execute
            on_finished: Callback for successful completion
            on_error: Callback for errors
            args: Positional arguments for task
            kwargs: Keyword arguments for task
        """
        kwargs = kwargs or {}
        
        if len(self._active_workers) < self._max_workers:
            self._start_task(task, args, kwargs, on_finished, on_error)
        else:
            # Queue for later
            self._pending_tasks.append((task, args, kwargs, on_finished, on_error))
    
    def _start_task(
        self,
        task: Callable,
        args: Tuple,
        kwargs: Dict,
        on_finished: Optional[Callable],
        on_error: Optional[Callable]
    ):
        """Start a task immediately."""
        worker = BackgroundWorker(self)
        worker.set_task(task, *args, **kwargs)
        
        if on_finished:
            worker.finished.connect(on_finished)
        if on_error:
            worker.error.connect(on_error)
        
        # Track worker and handle completion
        self._active_workers.append(worker)
        worker.finished.connect(lambda r: self._on_worker_done(worker))
        worker.error.connect(lambda m, e: self._on_worker_done(worker))
        
        worker.start()
    
    def _on_worker_done(self, worker: BackgroundWorker):
        """Handle worker completion."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
        
        # Start next pending task
        if self._pending_tasks:
            task, args, kwargs, on_finished, on_error = self._pending_tasks.pop(0)
            self._start_task(task, args, kwargs, on_finished, on_error)
        elif not self._active_workers:
            self.all_finished.emit()
    
    def active_count(self) -> int:
        """Return number of currently active workers."""
        return len(self._active_workers)
    
    def pending_count(self) -> int:
        """Return number of pending tasks."""
        return len(self._pending_tasks)
    
    def wait_all(self):
        """Wait for all tasks to complete (blocking)."""
        for worker in self._active_workers:
            if worker._thread:
                worker._thread.wait()
    
    def cancel_pending(self):
        """Cancel all pending (not yet started) tasks."""
        self._pending_tasks.clear()


def run_in_background(
    task: Callable,
    on_finished: Optional[Callable[[Any], None]] = None,
    on_error: Optional[Callable[[str, Exception], None]] = None,
    on_progress: Optional[Callable[[int, str], None]] = None,
    args: Tuple = (),
    kwargs: Optional[Dict] = None
) -> BackgroundWorker:
    """Convenience function to run a task in the background.
    
    This is the simplest way to run a non-blocking task.
    
    Args:
        task: Callable to execute in background
        on_finished: Callback for successful completion
        on_error: Callback for errors
        on_progress: Callback for progress updates
        args: Positional arguments for task
        kwargs: Keyword arguments for task
    
    Returns:
        BackgroundWorker instance (can be used to check status or cancel)
    
    Example:
        def load_data(path):
            # Expensive operation
            return data
        
        run_in_background(
            load_data,
            on_finished=lambda data: update_ui(data),
            on_error=lambda msg, e: show_error(msg),
            args=("data.json",)
        )
    """
    kwargs = kwargs or {}
    
    worker = BackgroundWorker()
    worker.set_task(task, *args, **kwargs)
    
    if on_finished:
        worker.finished.connect(on_finished)
    if on_error:
        worker.error.connect(on_error)
    if on_progress:
        worker.progress.connect(on_progress)
    
    worker.start()
    return worker


# Global worker pool singleton for simple usage
_global_pool: Optional[WorkerPool] = None


def get_worker_pool(max_workers: int = 4) -> WorkerPool:
    """Get or create the global worker pool.
    
    Args:
        max_workers: Maximum concurrent workers (only used on first call)
    
    Returns:
        Global WorkerPool instance
    """
    global _global_pool
    if _global_pool is None:
        _global_pool = WorkerPool(max_workers)
    return _global_pool
