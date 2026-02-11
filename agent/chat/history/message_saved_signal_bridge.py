"""Qt signal bridge for message_saved events.

This module bridges blinker signals to Qt signals, enabling automatic
QueuedConnection for thread-safe UI updates.
"""

import logging
from typing import Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class MessageSavedSignalBridge(QObject):
    """Bridges blinker message_saved signal to Qt signal.

    Qt signals automatically use QueuedConnection when connecting
    across threads, making them safe for UI updates from background
    threads.

    Usage:
        bridge = MessageSavedSignalBridge()
        bridge.message_saved.connect(lambda ws, proj, msg_id, gsn, curr: ...)

        # The bridge automatically connects to blinker signal on init
        # and converts it to Qt signal emission
    """

    # Qt signal - automatically uses QueuedConnection when connected across threads
    message_saved = Signal(str, str, str, int, int)  # workspace, project, message_id, gsn, current_gsn

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the signal bridge.

        Automatically connects to the blinker message_saved signal.
        """
        super().__init__(parent)
        self._connected = False
        self._connect_to_blinker()

    def _connect_to_blinker(self) -> None:
        """Connect to the blinker message_saved signal."""
        try:
            from agent.chat.history.agent_chat_history_service import message_saved as blinker_signal
            blinker_signal.connect(self._on_blinker_message_saved, weak=False)
            self._connected = True
            logger.debug("SignalBridge connected to blinker message_saved")
        except Exception as e:
            logger.error(f"Error connecting to blinker signal: {e}", exc_info=True)

    def _on_blinker_message_saved(
        self,
        sender,
        workspace_path: str,
        project_name: str,
        message_id: str,
        gsn: int,
        current_gsn: int
    ) -> None:
        """Handle blinker signal and convert to Qt signal.

        Args:
            sender: Signal sender
            workspace_path: Path to workspace
            project_name: Name of project
            message_id: ID of saved message
            gsn: Global sequence number of saved message
            current_gsn: Current (latest) GSN in system
        """
        try:
            # Emit Qt signal - automatic QueuedConnection ensures thread safety
            self.message_saved.emit(
                workspace_path,
                project_name,
                message_id,
                gsn,
                current_gsn
            )
        except Exception as e:
            logger.error(f"Error emitting Qt signal: {e}", exc_info=True)

    def disconnect(self) -> None:
        """Disconnect from the blinker signal."""
        if self._connected:
            try:
                from agent.chat.history.agent_chat_history_service import message_saved as blinker_signal
                blinker_signal.disconnect(self._on_blinker_message_saved)
                self._connected = False
                logger.debug("SignalBridge disconnected from blinker")
            except Exception:
                pass  # Signal might not be connected


# Global singleton instance
_global_bridge: Optional[MessageSavedSignalBridge] = None


def get_signal_bridge() -> MessageSavedSignalBridge:
    """Get the global message saved signal bridge.

    Returns:
        Global MessageSavedSignalBridge instance
    """
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = MessageSavedSignalBridge()
    return _global_bridge


def reset_global_bridge() -> None:
    """Reset the global bridge (useful for testing)."""
    global _global_bridge
    if _global_bridge is not None:
        _global_bridge.disconnect()
        _global_bridge = None
