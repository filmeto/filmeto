"""Test to verify the updated implementation for BaseMessageCard using BaseStructuredContentWidget list."""

import unittest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import sys

from app.ui.chat.card import BaseMessageCard
from app.ui.chat.message.text_content_widget import TextContentWidget
from app.ui.chat.message.skill_content_widget import SkillContentWidget
from app.ui.chat.message.code_block_widget import CodeBlockWidget
from app.ui.chat.message.link_widget import LinkWidget
from app.ui.chat.message.table_widget import TableWidget
from app.ui.chat.message.button_widget import ButtonWidget
from agent.chat.agent_chat_message import StructureContent, ContentType


class TestBaseMessageCardStructuredContentList(unittest.TestCase):
    """Test to verify the updated implementation for BaseMessageCard using BaseStructuredContentWidget list."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_base_message_card_uses_structured_content_widgets(self):
        """Test that BaseMessageCard now uses BaseStructuredContentWidget objects."""
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
        
        # Check that the main content widget is a TextContentWidget
        self.assertTrue(hasattr(card, 'main_content_widget'))
        self.assertIsInstance(card.main_content_widget, TextContentWidget)
        
        # Check that the card has a structured content layout
        self.assertTrue(hasattr(card, 'structured_content_layout'))
        
        # Add a structured content widget
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
        
        # Add the structure content widget
        card.add_structure_content_widget(structure_content)
        
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
        
        # Check that the structured content was added to the layout
        layout_count = card.structured_content_layout.count()
        self.assertGreater(layout_count, 0)
        
        # Check that the main content widget is still there
        main_widget_found = False
        for i in range(layout_count):
            widget = card.structured_content_layout.itemAt(i).widget()
            if widget == card.main_content_widget:
                main_widget_found = True
                break
        self.assertTrue(main_widget_found, "Main content widget should be in the layout")
        
        print(f"BaseMessageCard now uses structured content widgets: {layout_count} widgets in layout")
        
        # Clean up
        card.deleteLater()
    
    def test_adding_multiple_structured_content_widgets(self):
        """Test adding multiple structured content widgets."""
        # Create a BaseMessageCard
        card = BaseMessageCard(
            content="Test message with multiple structured content",
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
        
        # Add a skill content widget
        skill_data = {
            "status": "completed",
            "skill_name": "Test Skill",
            "message": "This is a test skill execution",
            "result": "Skill executed successfully"
        }
        
        skill_structure = StructureContent(
            content_type=ContentType.SKILL,
            data=skill_data,
            title="Test Skill Execution",
            description="Testing skill execution display"
        )
        
        card.add_structure_content_widget(skill_structure)
        
        # Add a code block widget
        code_data = {
            "language": "python",
            "code": "def hello():\n    print('Hello, World!')"
        }
        
        code_structure = StructureContent(
            content_type=ContentType.CODE_BLOCK,
            data=code_data,
            title="Sample Code",
            description="Testing code block"
        )
        
        card.add_structure_content_widget(code_structure)
        
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
        
        # Check that both structured content widgets were added
        layout_count = card.structured_content_layout.count()
        self.assertGreater(layout_count, 1, "Should have main content plus 2 structured content widgets")
        
        # Count the number of structured content widgets (excluding main content)
        structured_widget_count = 0
        for i in range(layout_count):
            widget = card.structured_content_layout.itemAt(i).widget()
            if widget and widget != card.main_content_widget:
                structured_widget_count += 1
        
        self.assertEqual(structured_widget_count, 2, "Should have 2 structured content widgets added")
        
        print(f"Added {structured_widget_count} structured content widgets to the card")
        
        # Clean up
        card.deleteLater()
    
    def test_content_methods_still_work(self):
        """Test that content methods still work after the changes."""
        # Create a BaseMessageCard
        card = BaseMessageCard(
            content="Initial content",
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
        
        # Test get_content method
        initial_content = card.get_content()
        self.assertEqual(initial_content, "Initial content")
        
        # Test set_content method
        card.set_content("Updated content")
        updated_content = card.get_content()
        self.assertEqual(updated_content, "Updated content")
        
        # Test append_content method
        card.append_content(" - appended")
        appended_content = card.get_content()
        self.assertEqual(appended_content, "Updated content - appended")
        
        print(f"Content methods work correctly: '{appended_content}'")
        
        # Clean up
        card.deleteLater()


def run_tests():
    """Run the tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()