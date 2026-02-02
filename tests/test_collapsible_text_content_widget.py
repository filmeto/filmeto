"""
Test CollapsibleTextContentWidget functionality.

Tests the collapsible text content widget's ability to:
1. Display long text with collapse/expand functionality
2. Show scroll area for content
3. Automatically collapse long content
4. Handle expand/collapse state changes
"""

import pytest
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.chat.content import TextContent
from app.ui.chat.message.collapsible_text_content_widget import CollapsibleTextContentWidget


class TestCollapsibleTextContentWidget:
    """Tests for CollapsibleTextContentWidget."""

    def setup_method(self):
        """Set up Qt application for testing."""
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

    def test_short_content_not_collapsed(self):
        """Test that content defaults to collapsed state."""
        content = TextContent(
            text="This is a short text content.",
            title="Short Content",
            description="A short description"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # All content defaults to collapsed
        assert widget.is_expanded() is False
        assert widget._auto_collapsed is True

    def test_long_content_auto_collapsed(self):
        """Test that long content is auto-collapsed."""
        long_text = "This is a very long text content. " * 50  # ~1000 characters

        content = TextContent(
            text=long_text,
            title="Long Content",
            description="A long description"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Long content should be auto-collapsed
        assert widget.is_expanded() is False
        assert widget._auto_collapsed is True

    def test_toggle_expand_collapse(self):
        """Test toggling expand/collapse state."""
        long_text = "This is a very long text content. " * 50

        content = TextContent(
            text=long_text,
            title="Toggle Test",
            description="Testing toggle functionality"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Initially collapsed
        assert widget.is_expanded() is False

        # Expand
        widget.set_expanded(True)
        assert widget.is_expanded() is True

        # Collapse
        widget.set_expanded(False)
        assert widget.is_expanded() is False

    def test_header_click_toggles(self):
        """Test that clicking the header toggles expand/collapse."""
        long_text = "This is a very long text content. " * 50

        content = TextContent(
            text=long_text,
            title="Header Click Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Initially collapsed
        assert widget.is_expanded() is False

        # Simulate header click (in Qt, this would trigger through mousePressEvent)
        from PySide6.QtGui import QMouseEvent, QCursor

        # We can't easily test mouse events without a full event loop,
        # so we'll just call the toggle method directly
        widget._toggle_expand()

        # Should now be expanded
        assert widget.is_expanded() is True

    def test_expand_button_changes(self):
        """Test that expand button icon changes correctly."""
        long_text = "This is a very long text content. " * 50

        content = TextContent(
            text=long_text,
            title="Button Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Collapsed state shows right arrow
        assert widget.expand_button.text() == "▶"

        # Expand
        widget.set_expanded(True)
        assert widget.expand_button.text() == "▼"

        # Collapse
        widget.set_expanded(False)
        assert widget.expand_button.text() == "▶"

    def test_scroll_area_limits_height_when_collapsed(self):
        """Test that scroll area has limited height when collapsed."""
        long_text = "This is a very long text content. " * 100

        content = TextContent(
            text=long_text,
            title="Scroll Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # When collapsed, max height should be limited
        assert widget.scroll_area.maximumHeight() == 150

        # Expand
        widget.set_expanded(True)
        # When expanded, max height should be larger
        assert widget.scroll_area.maximumHeight() >= 150

    def test_scroll_area_allows_scrolling(self):
        """Test that scroll area allows scrolling when content is long."""
        long_text = "\n".join([f"Line {i}" for i in range(100)])

        content = TextContent(
            text=long_text,
            title="Scroll Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Expand to see if scrolling works
        widget.set_expanded(True)

        # Content should have a size hint
        content_size_hint = widget.content_label.sizeHint()
        assert content_size_hint.height() > 0

        # Scroll area should be scrollable
        assert widget.scroll_area.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
        assert widget.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded

    def test_content_is_selectable(self):
        """Test that text content can be selected."""
        long_text = "This is a very long text content. " * 50

        content = TextContent(
            text=long_text,
            title="Selection Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Check that text selection is enabled
        flags = widget.content_label.textInteractionFlags()
        assert flags & Qt.TextSelectableByMouse

    def test_update_content_with_different_length(self):
        """Test updating content with different lengths."""
        # Start with short content
        short_content = TextContent(
            text="Short content",
            title="Update Test"
        )

        widget = CollapsibleTextContentWidget(
            short_content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Should be collapsed (all content defaults to collapsed)
        assert widget.is_expanded() is False

        # Update with long content
        long_text = "This is a very long text content. " * 50
        long_content = TextContent(
            text=long_text,
            title="Update Test"
        )

        widget.update_content(long_content)

        # Should remain collapsed (content update doesn't auto-expand)
        assert widget.is_expanded() is False
        # Verify content was updated
        assert widget.structure_content.text == long_text

    def test_get_state(self):
        """Test getting widget state."""
        long_text = "This is a very long text content. " * 50

        content = TextContent(
            text=long_text,
            title="State Test"
        )

        widget = CollapsibleTextContentWidget(
            content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        state = widget.get_state()

        assert state["title"] == "State Test"
        assert state["text"] == long_text
        assert "is_expanded" in state
        assert "is_auto_collapsed" in state

    def test_set_state(self):
        """Test setting widget state."""
        initial_content = TextContent(
            text="Initial content",
            title="Set State Test"
        )

        widget = CollapsibleTextContentWidget(
            initial_content,
            max_lines_collapsed=3,
            auto_collapse_threshold=300
        )

        # Set new state
        new_state = {
            "title": "Updated Title",
            "text": "Updated content text",
            "is_expanded": True
        }

        widget.set_state(new_state)

        # Verify updates
        assert widget.structure_content.title == "Updated Title"
        assert widget.structure_content.text == "Updated content text"
        assert widget.is_expanded() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
