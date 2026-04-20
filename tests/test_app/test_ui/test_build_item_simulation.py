#!/usr/bin/env python3
"""Simulate the actual history loading process."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging to see debug messages
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from agent.chat.content import TextContent, StructureContent
from agent.chat.agent_chat_message import AgentMessage
from app.ui.chat.list.agent_chat_list_items import ChatListItem, MessageGroup
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel


def test_build_item_from_history():
    """Test _build_item_from_history method with actual data."""
    from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

    print("\n" + "=" * 70)
    print(" _build_item_from_history Simulation Test")
    print("=" * 70)

    # Create mock widget instance (just for accessing the method)
    class MockWidget:
        def _resolve_agent_metadata(self, sender, metadata=None):
            return "#4a90e2", "🤖", {}

    mock_widget = MockWidget()

    # Monkey patch the method to our mock
    from app.ui.chat.list import agent_chat_list_widget
    original_resolve = qml_agent_chat_list_widget.QmlAgentChatListWidget._resolve_agent_metadata
    qml_agent_chat_list_widget.QmlAgentChatListWidget._resolve_agent_metadata = MockWidget._resolve_agent_metadata

    try:
        # Import the method
        from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
        build_method = QmlAgentChatListWidget._build_item_from_history

        # Test case 1: Normal text message
        print("\n--- Test 1: Normal text message ---")
        msg_data = {
            "message_id": "msg-001",
            "sender_id": "agent",
            "sender_name": "Test Agent",
            "timestamp": "2025-02-08T12:00:00",
            "structured_content": [
                {
                    "content_id": "content-1",
                    "content_type": "text",
                    "title": None,
                    "description": None,
                    "data": {"text": "This is a test message"},
                    "metadata": {},
                    "status": "completed",
                    "parent_id": None
                }
            ]
        }

        result = build_method(mock_widget, msg_data)
        if result:
            print(f"✓ ChatListItem created:")
            print(f"  sender_name: {result.sender_name}")
            print(f"  is_user: {result.is_user}")
            if result.agent_message:
                print(f"  agent_message.structured_content: {result.agent_message.structured_content}")
                print(f"  Length: {len(result.agent_message.structured_content)}")

                # Convert to QML format
                qml_item = QmlAgentChatListModel.from_chat_list_item(result)
                print(f"\n  QML format:")
                print(f"    senderName: {qml_item.get('senderName')}")
                print(f"    structuredContent: {qml_item.get('structuredContent')}")
        else:
            print("✗ Failed to create ChatListItem")

        # Test case 2: Message with multiple content items
        print("\n--- Test 2: Multiple content items ---")
        msg_data2 = {
            "message_id": "msg-002",
            "sender_id": "agent",
            "sender_name": "Test Agent",
            "timestamp": "2025-02-08T12:00:00",
            "structured_content": [
                {
                    "content_id": "content-1",
                    "content_type": "text",
                    "data": {"text": "First message"}
                },
                {
                    "content_id": "content-2",
                    "content_type": "thinking",
                    "data": {"thought": "Let me think..."}
                }
            ]
        }

        result2 = build_method(mock_widget, msg_data2)
        if result2:
            print(f"✓ ChatListItem created with {len(result2.agent_message.structured_content)} items")
            qml_item2 = QmlAgentChatListModel.from_chat_list_item(result2)
            print(f"  QML structuredContent length: {len(qml_item2.get('structuredContent', []))}")
        else:
            print("✗ Failed to create ChatListItem")

        # Test case 3: Old format (content in 'content' field)
        print("\n--- Test 3: Old format check ---")
        msg_data3 = {
            "message_id": "msg-003",
            "sender_id": "agent",
            "sender_name": "Test Agent",
            "timestamp": "2025-02-08T12:00:00",
            "content": [  # Old 'content' field instead of 'structured_content'
                {
                    "content_type": "text",
                    "text": "Old format message"
                }
            ]
        }

        result3 = build_method(mock_widget, msg_data3)
        if result3:
            print(f"✓ ChatListItem created (old format)")
            if result3.agent_message:
                print(f"  structured_content length: {len(result3.agent_message.structured_content)}")
        else:
            print("✗ Failed to create ChatListItem (old format)")

    finally:
        # Restore original method
        qml_agent_chat_list_widget.QmlAgentChatListWidget._resolve_agent_metadata = original_resolve


if __name__ == "__main__":
    test_build_item_from_history()
    print("\n" + "=" * 70)
    print(" Test completed")
    print("=" * 70)
