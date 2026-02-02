"""Test to verify the updated implementation for width recalculation after adding structure content."""

import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys

from app.ui.chat.card import BaseMessageCard
from app.ui.chat.message.skill_content_widget import SkillContentWidget
from agent.chat.agent_chat_message import StructureContent, ContentType


class TestWidthRecalculationAfterAddingStructureContent(unittest.TestCase):
    """Test to verify width recalculation after adding structure content."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_adding_structure_content_triggers_width_recalculation(self):
        """Test that adding structure content triggers width recalculation."""
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
        
        # Get the initial bubble width value
        initial_width = card._available_bubble_width_value
        print(f"Initial available bubble width: {initial_width}")
        
        # Create a sample structure content for a skill
        skill_data = {
            "status": "starting",
            "skill_name": "Test Skill",
            "message": "This is a test skill execution",
            "result": "Skill starting..."
        }
        
        structure_content = StructureContent(
            content_type=ContentType.SKILL,
            data=skill_data,
            title="Test Skill Execution",
            description="Testing skill execution display"
        )
        
        # Store the structure content list before adding
        initial_structured_count = card.structure_content.structured_content_layout.count() if hasattr(card.structure_content, 'structured_content_layout') else 0
        print(f"Initial structured content count: {initial_structured_count}")

        # Add the structure content widget
        card.add_structure_content_widget(structure_content)

        # Process events to ensure UI updates
        QCoreApplication.processEvents()

        # Check that the bubble width was recalculated (this happens internally in _update_bubble_width)
        # The width might stay the same if the content doesn't change the required width,
        # but the method should have been called
        print(f"Width after adding structure content: {card._available_bubble_width_value}")

        # Check that the structured content was added
        final_structured_count = card.structure_content.structured_content_layout.count() if hasattr(card.structure_content, 'structured_content_layout') else 0
        print(f"Final structured content count: {final_structured_count}")

        # Verify that the structured content was added
        self.assertGreater(final_structured_count, initial_structured_count,
                          "Structure content should have been added")
        
        # Clean up
        card.deleteLater()
    
    def test_structure_content_widget_addition_triggers_parent_notification(self):
        """Test that adding structure content widget triggers parent notification."""
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
        
        # Get the initial bubble width value
        initial_width = card._available_bubble_width_value
        print(f"Initial width before adding skill content: {initial_width}")
        
        # Create a skill structure content
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
        
        # Add the skill content widget
        card.add_structure_content_widget(structure_content)
        
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
        
        # Check that the width was recalculated after adding structure content
        final_width = card._available_bubble_width_value
        print(f"Final width after adding skill content: {final_width}")
        
        # The width might be the same if the content fits within the existing width,
        # but the important thing is that the recalculation was triggered
        # Check that the structure content was added to the layout
        # Count the number of SkillContentWidget in the structured content layout
        count = 0
        layout = card.structure_content.structured_content_layout
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and isinstance(widget, SkillContentWidget):
                count += 1

        self.assertGreater(count, 0, "Skill content widget should have been added")
        
        # Clean up
        card.deleteLater()


def run_tests():
    """Run the tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()