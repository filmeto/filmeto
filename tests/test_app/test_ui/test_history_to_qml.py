#!/usr/bin/env python3
"""Test complete flow from history loading to QML display."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.chat.content import TextContent, StructureContent
from agent.chat.agent_chat_message import AgentMessage
from app.ui.chat.list.agent_chat_list_items import ChatListItem
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
import json


def test_history_to_qml_flow():
    """Test the complete flow from history data to QML model."""

    print("\n" + "=" * 70)
    print(" History to QML Flow Test")
    print("=" * 70)

    # Step 1: Simulate history data (as stored in JSON)
    print("\n--- Step 1: Simulate history data (from JSON) ---")
    history_data = {
        "message_id": "test-msg-123",
        "sender_id": "test_agent",
        "sender_name": "Test Agent",
        "timestamp": "2025-02-08T12:00:00",
        "structured_content": [
            {
                "content_id": "content-1",
                "content_type": "text",
                "title": None,
                "description": None,
                "data": {"text": "Hello from history!"},
                "metadata": {},
                "status": "creating",
                "parent_id": None
            }
        ]
    }
    print(f"History data:")
    print(f"  message_id: {history_data['message_id']}")
    print(f"  sender_name: {history_data['sender_name']}")
    print(f"  structured_content: {json.dumps(history_data['structured_content'], indent=4)}")

    # Step 2: Parse structured_content from history
    print("\n--- Step 2: Parse structured_content ---")
    content_list = history_data.get("structured_content", [])
    print(f"Content list length: {len(content_list)}")

    structured_content = []
    for i, content_item in enumerate(content_list):
        if isinstance(content_item, dict):
            try:
                sc = StructureContent.from_dict(content_item)
                structured_content.append(sc)
                print(f"  [{i}] Parsed: {type(sc).__name__} - content_type={sc.content_type}")
                if hasattr(sc, 'text'):
                    print(f"      text: {sc.text}")
            except Exception as e:
                print(f"  [{i}] Failed: {e}")
                print(f"      content_item: {content_item}")

    # Step 3: Create AgentMessage
    print("\n--- Step 3: Create AgentMessage ---")
    agent_message = AgentMessage(
        sender_id=history_data["sender_id"],
        sender_name=history_data["sender_name"],
        message_id=history_data["message_id"],
        structured_content=structured_content,
        metadata={"timestamp": history_data["timestamp"]}
    )
    print(f"AgentMessage created:")
    print(f"  sender_name: {agent_message.sender_name}")
    print(f"  structured_content length: {len(agent_message.structured_content)}")

    # Step 4: Create ChatListItem
    print("\n--- Step 4: Create ChatListItem ---")
    chat_item = ChatListItem(
        message_id=agent_message.message_id,
        sender_id=agent_message.sender_id,
        sender_name=agent_message.sender_name,
        is_user=False,
        agent_message=agent_message,
    )
    print(f"ChatListItem created:")
    print(f"  sender_name: {chat_item.sender_name}")
    print(f"  agent_message.structured_content length: {len(chat_item.agent_message.structured_content)}")

    # Step 5: Convert to QML format
    print("\n--- Step 5: Convert to QML format ---")
    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)
    print(f"QML item keys: {list(qml_item.keys())}")
    print(f"  senderName: {qml_item.get('senderName')}")
    print(f"  structuredContent: {json.dumps(qml_item.get('structuredContent'), indent=4)}")

    # Step 6: Check if data is correct for QML
    print("\n--- Step 6: QML data validation ---")
    structured_content_qml = qml_item.get('structuredContent', [])
    if not structured_content_qml:
        print("✗ ERROR: structuredContent is empty!")
        return False

    print(f"✓ structuredContent has {len(structured_content_qml)} items")

    # Check first item
    first_item = structured_content_qml[0]
    content_type = first_item.get('content_type')
    data = first_item.get('data', {})

    print(f"  First item:")
    print(f"    content_type: {content_type}")
    print(f"    data: {data}")

    if content_type == "text" and data.get('text') == "Hello from history!":
        print("✓ Data is correct!")
        return True
    else:
        print("✗ Data is incorrect!")
        return False


def test_empty_structured_content():
    """Test what happens when structured_content is empty."""

    print("\n" + "=" * 70)
    print(" Empty structuredContent Test")
    print("=" * 70)

    # Create message with empty structured_content
    agent_message = AgentMessage(
        sender_id="test_agent",
        sender_name="Test Agent",
        message_id="test-msg-empty",
        structured_content=[],
    )

    chat_item = ChatListItem(
        message_id="test-msg-empty",
        sender_id="test_agent",
        sender_name="Test Agent",
        is_user=False,
        agent_message=agent_message,
    )

    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    structured_content_qml = qml_item.get('structuredContent', [])
    print(f"structuredContent: {structured_content_qml}")
    print(f"Length: {len(structured_content_qml)}")

    if not structured_content_qml:
        print("✓ Empty structuredContent handled correctly")
        return True
    else:
        print("✗ Expected empty structuredContent")
        return False


if __name__ == "__main__":
    result1 = test_history_to_qml_flow()
    result2 = test_empty_structured_content()

    print("\n" + "=" * 70)
    if result1 and result2:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 70)
