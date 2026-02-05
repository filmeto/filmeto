"""
Test script to verify chat history widget layout optimization
"""
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer
from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from app.data.workspace import Workspace


def test_chat_history_layout():
    """Test the optimized chat history layout"""
    print("Testing chat history layout optimization...")
    
    # Create a QApplication instance
    app = QApplication(sys.argv)
    
    # Create a temporary directory for the workspace
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a workspace
        workspace = Workspace(workspace_path=temp_dir, project_name="test_project")
        
        # Create the chat history widget
        chat_widget = AgentChatListWidget(workspace)
        
        # Create a main window to show the widget
        window = QWidget()
        layout = QVBoxLayout(window)
        layout.addWidget(chat_widget)
        window.setWindowTitle("Chat History Layout Test")
        window.resize(800, 600)
        
        # Add a user message
        chat_widget.add_user_message("This is a user message to test the layout.")
        
        # Add an agent message
        message_id = chat_widget.start_streaming_message("Test Agent")
        chat_widget.update_streaming_message(message_id, "This is an agent message to test the layout.")
        
        # Show the window
        window.show()
        
        # Add a timer to close the application after 5 seconds
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(5000)  # Close after 5 seconds
        
        print("Chat history layout test window opened. Will close in 5 seconds.")
        
        # Start the event loop
        app.exec()


if __name__ == "__main__":
    test_chat_history_layout()