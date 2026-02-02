"""Test to verify the updated skill content widget width implementation."""

import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
import sys

from app.ui.chat.card import BaseMessageCard
from app.ui.chat.message.skill_content_widget import SkillContentWidget
from app.ui.chat.message.structure_content_widget import StructureContentWidget
from agent.chat.agent_chat_message import StructureContent, ContentType


class TestUpdatedSkillContentWidgetWidth(unittest.TestCase):
    """Test to verify the updated skill content widget width implementation."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_structure_content_widget_receives_available_width(self):
        """Test that StructureContentWidget receives the available width."""
        # Create a mock parent widget
        parent_widget = QWidget()
        parent_widget.resize(500, 300)
        parent_widget.show()
        
        # Create StructureContentWidget with available width
        available_width = 400
        structure_widget = StructureContentWidget("Test content", parent_widget, available_width)
        
        # Check that the available width was stored
        self.assertEqual(structure_widget.available_width, available_width)
        
        # Clean up
        structure_widget.deleteLater()
        parent_widget.deleteLater()
    
    def test_skill_content_widget_receives_available_width(self):
        """Test that SkillContentWidget receives and uses the available width."""
        # Create a sample structure content for a skill
        skill_data = {
            "status": "completed",
            "skill_name": "Test Skill",
            "message": "This is a test skill execution",
            "result": "Skill executed successfully"
        }
        
        structure_content = StructureContent(
            content_type=ContentType.SKILL,
            data=skill_data,
            title="Test Skill Execution",
            description="Testing skill execution display"
        )
        
        # Create a parent widget
        parent_widget = QWidget()
        parent_widget.show()
        
        # Create SkillContentWidget with available width
        available_width = 350
        skill_widget = SkillContentWidget(structure_content, parent_widget, available_width)
        
        # Check that the available width was stored and applied
        self.assertEqual(skill_widget.available_width, available_width)
        self.assertLessEqual(skill_widget.container_frame.maximumWidth(), available_width)
        
        # Test the update_available_width method
        new_width = 300
        skill_widget.update_available_width(new_width)
        self.assertEqual(skill_widget.available_width, new_width)
        self.assertLessEqual(skill_widget.container_frame.maximumWidth(), new_width)
        
        # Clean up
        skill_widget.deleteLater()
        parent_widget.deleteLater()
    
    def test_base_message_card_holds_available_width(self):
        """Test that BaseMessageCard holds and updates the available width."""
        from PySide6.QtCore import Qt
        # Create a BaseMessageCard
        card = BaseMessageCard(
            content="Test message",
            sender_name="Test User",
            icon="👤",
            color="#35373a",
            parent=None,
            alignment=Qt.AlignRight,
            background_color="#35373a",
            text_color="#e1e1e1",
            avatar_size=42
        )
        
        card.resize(600, 400)
        card.show()
        
        # Process events to ensure UI is set up
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
        
        # Check that the available width value is stored
        initial_width = card._available_bubble_width_value
        self.assertIsInstance(initial_width, int)
        self.assertGreater(initial_width, 0)
        
        # Check that the structure content widget received the available width
        self.assertEqual(card.structure_content.available_width, initial_width)
        
        # Clean up
        card.deleteLater()


def run_tests():
    """Run the tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()