"""Test to verify the updated implementation for calculating structure content width."""

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


class TestStructureContentWidthCalculation(unittest.TestCase):
    """Test to verify the updated implementation for calculating structure content width."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_text_content_widget_get_width(self):
        """Test that TextContentWidget implements get_width method."""
        # Create a sample structure content
        structure_content = StructureContent(
            content_type=ContentType.TEXT,
            data="This is a sample text content for testing.",
            title="Sample Text",
            description="Testing text content width calculation"
        )
        
        # Create a TextContentWidget
        widget = TextContentWidget(structure_content)
        
        # Test the get_width method
        max_width = 400
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"TextContentWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_skill_content_widget_get_width(self):
        """Test that SkillContentWidget implements get_width method."""
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
        
        # Create a SkillContentWidget
        widget = SkillContentWidget(structure_content)
        
        # Test the get_width method
        max_width = 400
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"SkillContentWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_code_block_widget_get_width(self):
        """Test that CodeBlockWidget implements get_width method."""
        # Create a sample structure content for a code block
        code_data = {
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')\n    return True"
        }
        
        structure_content = StructureContent(
            content_type=ContentType.CODE_BLOCK,
            data=code_data,
            title="Sample Code Block",
            description="Testing code block width calculation"
        )
        
        # Create a CodeBlockWidget
        widget = CodeBlockWidget(structure_content)
        
        # Test the get_width method
        max_width = 500
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"CodeBlockWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_link_widget_get_width(self):
        """Test that LinkWidget implements get_width method."""
        # Create a sample structure content for a link
        link_data = {
            "url": "https://www.example.com",
            "text": "Example Website"
        }
        
        structure_content = StructureContent(
            content_type=ContentType.LINK,
            data=link_data,
            title="Sample Link",
            description="Testing link width calculation"
        )
        
        # Create a LinkWidget
        widget = LinkWidget(structure_content)
        
        # Test the get_width method
        max_width = 300
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"LinkWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_table_widget_get_width(self):
        """Test that TableWidget implements get_width method."""
        # Create a sample structure content for a table
        table_data = {
            "headers": ["Name", "Age", "City"],
            "rows": [
                ["Alice", "30", "New York"],
                ["Bob", "25", "Los Angeles"],
                ["Charlie", "35", "Chicago"]
            ]
        }
        
        structure_content = StructureContent(
            content_type=ContentType.TABLE,
            data=table_data,
            title="Sample Table",
            description="Testing table width calculation"
        )
        
        # Create a TableWidget
        widget = TableWidget(structure_content)
        
        # Test the get_width method
        max_width = 600
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"TableWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_button_widget_get_width(self):
        """Test that ButtonWidget implements get_width method."""
        # Create a sample structure content for a button
        button_data = {
            "text": "Click Me",
            "action": "sample_action"
        }
        
        structure_content = StructureContent(
            content_type=ContentType.BUTTON,
            data=button_data,
            title="Sample Button",
            description="Testing button width calculation"
        )
        
        # Create a ButtonWidget
        widget = ButtonWidget(structure_content)
        
        # Test the get_width method
        max_width = 200
        calculated_width = widget.get_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"ButtonWidget width: {calculated_width} (max: {max_width})")
        
        # Clean up
        widget.deleteLater()
    
    def test_base_message_card_calculate_structure_content_width(self):
        """Test that BaseMessageCard uses the new _calculate_structure_content_width method."""
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
        
        # Test the new method
        max_width = 400
        calculated_width = card._calculate_structure_content_width(max_width)
        
        # The width should be greater than 0 and less than or equal to max_width
        self.assertGreater(calculated_width, 0)
        self.assertLessEqual(calculated_width, max_width)
        
        print(f"BaseMessageCard structure content width: {calculated_width} (max: {max_width})")
        
        # Clean up
        card.deleteLater()


def run_tests():
    """Run the tests."""
    unittest.main()


if __name__ == '__main__':
    run_tests()