"""
Test script to verify that crew colors are displayed correctly in actual conversation flow
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


def test_sub_agent_colors_in_conversation():
    """Test that crew colors are correctly displayed in conversation flow"""
    print("Testing crew colors in conversation flow...")
    
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
        window.setWindowTitle("Sub-Agent Color Test in Conversation Flow")
        window.resize(800, 600)
        
        # Test adding messages from different crew_members
        test_agents = [
            "director",
            "cinematographer", 
            "editor",
            "producer",
            "screenwriter",
            "sound_designer",
            "storyboard_artist",
            "vfx_supervisor"
        ]
        
        print("Adding messages from different crew_members...")
        for i, agent_name in enumerate(test_agents):
            # Create a message ID
            import uuid
            message_id = f"test_msg_{i}_{uuid.uuid4()}"
            
            # Use get_or_create_agent_card to simulate actual conversation flow
            card = chat_widget.get_or_create_agent_card(message_id, agent_name)
            chat_widget.update_agent_card(
                message_id,
                content=f"Test message from {agent_name}",
                append=False
            )
            print(f"  Added message from {agent_name}")
        
        # Show the window
        window.show()
        
        # Add a timer to close the application after 10 seconds
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)  # Close after 10 seconds
        
        print("Chat history widget test window opened. Shows messages from all crew_members with their respective colors.")
        print("Each crew should display with its configured color.")
        
        # Start the event loop
        app.exec()


if __name__ == "__main__":
    test_sub_agent_colors_in_conversation()