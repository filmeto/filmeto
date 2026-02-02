"""User message card widget for displaying user messages in chat."""

from PySide6.QtCore import Qt

from app.ui.chat.card.card_base import BaseMessageCard


class UserMessageCard(BaseMessageCard):
    """Card widget for displaying user messages."""

    def __init__(self, content: str, parent=None):
        """Initialize user message card."""
        super().__init__(
            content=content,
            sender_name="You",
            icon="👤",
            color="#35373a",
            parent=parent,
            alignment=Qt.AlignRight,
            background_color="#35373a",
            text_color="#e1e1e1"
        )

        # Update the object name and styling for user messages
        self.setObjectName("user_message_card")
        self.setStyleSheet("""
            QFrame#user_message_card {
                background-color: transparent;
                margin: 2px 0px;
            }
        """)

        # Update name label styling for user messages
        self.name_label.setStyleSheet("""
            QLabel {
                color: #35373a;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        # Update bubble styling for user messages
        self.bubble_container.setStyleSheet(f"""
            QFrame#message_bubble {{
                background-color: {self.background_color};
                border-radius: 5px;
            }}
        """)
