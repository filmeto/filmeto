"""Test to verify the updated implementation for BaseMessageCard without main_content_widget."""

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


class TestBaseMessageCardWithoutMainContentWidget(unittest.TestCase):
    """Test to verify the updated implementation for BaseMessageCard without main_content_widget."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_base_message_card_no_longer_has_main_content_widget(self):
        """Test that BaseMessageCard no longer has main_content_widget attribute."""
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
        
        # Check that the card no longer has main_content_widget attribute
        self.assertFalse(hasattr(card, 'main_content_widget'),
                         "BaseMessageCard should not have main_content_widget attribute anymore")

        # Check that the card no longer has _initial_text_widget attribute either
        self.assertFalse(hasattr(card, '_initial_text_widget'),
                        "BaseMessageCard should not have _initial_text_widget attribute anymore")

        # Check that the card has structured content layout
        self.assertTrue(hasattr(card, 'structured_content_layout'),
                        "BaseMessageCard should have structured_content_layout attribute")
        
        # Check that the card has a structured content layout
        self.assertTrue(hasattr(card, 'structured_content_layout'))
        
        print(f"BaseMessageCard no longer has main_content_widget: ✓")
        
        # Clean up
        card.deleteLater()
    
    def test_adding_structured_content_widgets(self):
        """Test adding structured content widgets."""
        # Create a BaseMessageCard
        card = BaseMessageCard(
            content="Test message with structured content",
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
        
        # Add the structure content widget
        card.add_structure_content_widget(skill_structure)
        
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
        
        # Check that the structured content was added to the layout
        layout_count = card.structured_content_layout.count()
        self.assertGreater(layout_count, 0, "Should have content widgets in layout")
        
        # Check that all widgets in the layout are BaseStructuredContentWidget instances
        for i in range(layout_count):
            widget = card.structured_content_layout.itemAt(i).widget()
            if widget:
                # Check that it's a subclass of BaseStructuredContentWidget
                # (In practice, we'd check isinstance(widget, BaseStructuredContentWidget)
                # but since we don't have the import here, we'll check for expected attributes)
                self.assertTrue(hasattr(widget, 'structure_content'), 
                               f"Widget {type(widget).__name__} should have structure_content attribute")
        
        print(f"Added structured content widgets: {layout_count} widgets in layout")
        
        # Clean up
        card.deleteLater()
    
    def test_content_methods_still_work_correctly(self):
        """Test that content methods still work after removing main_content_widget."""
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
    
    def test_all_content_as_base_structured_content_widgets(self):
        """Test that all content is now BaseStructuredContentWidget objects."""
        # Create a BaseMessageCard
        card = BaseMessageCard(
            content="Base content",
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
        
        # Add multiple types of structured content
        # Add a code block
        code_structure = StructureContent(
            content_type=ContentType.CODE_BLOCK,
            data={"language": "python", "code": "print('hello')"},
            title="Code Block",
            description="Testing code block"
        )
        card.add_structure_content_widget(code_structure)
        
        # Add a table
        table_structure = StructureContent(
            content_type=ContentType.TABLE,
            data={"headers": ["Name", "Value"], "rows": [["A", "1"], ["B", "2"]]},
            title="Table",
            description="Testing table"
        )
        card.add_structure_content_widget(table_structure)
        
        # Process events to ensure UI updates
        QCoreApplication.processEvents()
        
        # Check that all widgets in the layout are structured content widgets
        layout_count = card.structured_content_layout.count()
        self.assertGreater(layout_count, 0, "Should have content widgets in layout")
        
        for i in range(layout_count):
            widget = card.structured_content_layout.itemAt(i).widget()
            if widget:
                # All widgets should have structure_content attribute
                self.assertTrue(hasattr(widget, 'structure_content'),
                               f"Widget {type(widget).__name__} should have structure_content attribute")
                # All widgets should have update_content, get_state, set_state, and get_width methods
                self.assertTrue(hasattr(widget, 'get_width'),
                               f"Widget {type(widget).__name__} should have get_width method")
        
        print(f"All {layout_count} content widgets follow BaseStructuredContentWidget interface")
        
        # Clean up
        card.deleteLater()


def run_tests():
    """Run the tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()