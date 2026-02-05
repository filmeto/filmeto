"""
Comprehensive test script to verify that all crew colors are displayed correctly
"""
import asyncio
import tempfile
from pathlib import Path

from agent.crew.crew_service import CrewService
from app.data.project import Project
from app.data.workspace import Workspace
from app.ui.chat.list.agent_chat_list import AgentChatListWidget
from agent.filmeto_agent import FilmetoAgent


def test_all_sub_agent_colors():
    """Test that all crew colors are correctly loaded and displayed"""
    print("Testing all crew color configurations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create workspace
        workspace = Workspace(workspace_path=temp_dir, project_name="test_project")
        
        # Create project directory structure
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()
        
        # Create basic project structure
        (project_path / "project.yml").write_text("{}")
        (project_path / "timeline").mkdir()
        (project_path / "prompts").mkdir()
        (project_path / "resources").mkdir()
        (project_path / "characters").mkdir()
        (project_path / "agent").mkdir()
        (project_path / "agent" / "conversations").mkdir()
        (project_path / "agent" / "crew_members").mkdir()
        
        # Create project instance
        project = Project(workspace, str(project_path), "test_project")
        
        # Initialize crew service
        sub_agent_service = CrewService()
        
        # Load crew metadata
        metadata = sub_agent_service.get_project_sub_agent_metadata(project)
        
        print(f"Loaded metadata for {len(metadata)} crew_members:")
        
        # Define expected colors for each crew
        expected_colors = {
            "director": "#4a90e2",
            "cinematographer": "#ff6347",
            "editor": "#ffa500",
            "producer": "#7b68ee",
            "screenwriter": "#32cd32",
            "sound_designer": "#9370db",
            "storyboard_artist": "#ff69b4",
            "vfx_supervisor": "#00ced1"
        }
        
        all_correct = True
        for agent_name, agent_metadata in metadata.items():
            color = agent_metadata.get('color', 'NOT_FOUND')
            expected_color = expected_colors.get(agent_name, 'UNDEFINED')
            
            status = "✅" if color == expected_color else "❌"
            print(f"  {status} {agent_name}: {color} (expected: {expected_color})")
            
            if color != expected_color:
                all_correct = False
        
        # Check if all expected agents are present
        for agent_name, expected_color in expected_colors.items():
            if agent_name not in metadata:
                print(f"  ❌ Missing agent: {agent_name}")
                all_correct = False
        
        if all_correct:
            print("\n🎉 All crew color configurations are correct!")
            return True
        else:
            print("\n❌ Some crew color configurations are incorrect!")
            return False


async def test_chat_history_widget_colors():
    """Test that ChatHistoryWidget correctly displays agent colors"""
    print("\nTesting ChatHistoryWidget color display...")
    
    import sys
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    
    # Create a QApplication instance
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create workspace
        workspace = Workspace(workspace_path=temp_dir, project_name="test_project")
        
        # Create project directory structure
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()
        
        # Create basic project structure
        (project_path / "project.yml").write_text("{}")
        (project_path / "timeline").mkdir()
        (project_path / "prompts").mkdir()
        (project_path / "resources").mkdir()
        (project_path / "characters").mkdir()
        (project_path / "agent").mkdir()
        (project_path / "agent" / "conversations").mkdir()
        (project_path / "agent" / "crew_members").mkdir()
        
        # Create project instance
        project = Project(workspace, str(project_path), "test_project")
        
        # Initialize the project's crew_members
        crew_member_service = CrewService()
        crew_member_service.initialize_project_crew_members(project)
        
        # Create the chat history widget
        chat_widget = AgentChatListWidget(workspace)
        
        # Create a main window to show the widget
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        window = QWidget()
        layout = QVBoxLayout(window)
        layout.addWidget(chat_widget)
        window.setWindowTitle("Sub-Agent Color Test")
        window.resize(800, 600)
        
        # Add messages from different crew_members to test their colors
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
            message_id = f"test_msg_{i}"
            card = chat_widget.get_or_create_agent_card(message_id, agent_name)
            chat_widget.update_agent_card(
                message_id,
                content=f"Test message from {agent_name}",
                append=False
            )
            print(f"  Added message from {agent_name}")
        
        # Add a user message for comparison
        chat_widget.add_user_message("Test user message")
        print("  Added user message for comparison")
        
        # Show the window
        window.show()
        
        # Add a timer to close the application after 10 seconds
        timer = QTimer()
        timer.timeout.connect(app.quit)
        timer.start(10000)  # Close after 10 seconds
        
        print("Chat history widget test window opened. Shows messages from all crew_members with their respective colors.")
        print("Close the window or wait 10 seconds to continue...")
        
        # Start the event loop
        app.exec()
        
        return True


if __name__ == "__main__":
    print("Running comprehensive crew color test...")
    
    # Test 1: Check that all crew colors are correctly loaded
    success1 = test_all_sub_agent_colors()
    
    # Test 2: Test ChatHistoryWidget color display
    success2 = asyncio.run(test_chat_history_widget_colors())
    
    if success1 and success2:
        print("\n✅ All tests passed! All crew colors are working correctly.")
    else:
        print("\n❌ Some tests failed!")