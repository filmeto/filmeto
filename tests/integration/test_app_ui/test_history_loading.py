#!/usr/bin/env python3
"""Test history loading to diagnose structured content issues."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agent.chat.content import StructureContent, TextContent
from agent.chat.agent_chat_types import ContentType
import json


def test_structure_content_from_dict():
    """Test StructureContent.from_dict() with different data formats."""

    print("\n" + "=" * 70)
    print(" StructureContent.from_dict() Test")
    print("=" * 70)

    # Test 1: Full format (from to_dict())
    print("\n--- Test 1: Full format (from to_dict()) ---")
    full_format = {
        "content_id": "test-1",
        "content_type": "text",
        "title": None,
        "description": None,
        "data": {"text": "Hello World"},
        "metadata": {},
        "status": "creating",
        "parent_id": None
    }
    print(f"Input: {json.dumps(full_format, indent=2)}")

    try:
        result = StructureContent.from_dict(full_format)
        print(f"✓ Success: {result}")
        print(f"  Type: {type(result)}")
        print(f"  content_type: {result.content_type}")
        if hasattr(result, 'text'):
            print(f"  text: {result.text}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Test 2: Minimal format
    print("\n--- Test 2: Minimal format ---")
    minimal_format = {
        "content_type": "text",
        "data": {"text": "Hello World"}
    }
    print(f"Input: {json.dumps(minimal_format, indent=2)}")

    try:
        result = StructureContent.from_dict(minimal_format)
        print(f"✓ Success: {result}")
        print(f"  Type: {type(result)}")
        print(f"  content_type: {result.content_type}")
        if hasattr(result, 'text'):
            print(f"  text: {result.text}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Test 3: Test format with text at top level
    print("\n--- Test 3: Format with text at top level (old format?) ---")
    old_format = {
        "content_type": "text",
        "text": "Hello World"
    }
    print(f"Input: {json.dumps(old_format, indent=2)}")

    try:
        result = StructureContent.from_dict(old_format)
        print(f"✓ Success: {result}")
        print(f"  Type: {type(result)}")
        print(f"  content_type: {result.content_type}")
        if hasattr(result, 'text'):
            print(f"  text: {result.text}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Test 4: Direct TextContent.from_dict()
    print("\n--- Test 4: Direct TextContent.from_dict() ---")
    try:
        result = TextContent.from_dict(full_format)
        print(f"✓ Success: {result}")
        print(f"  Type: {type(result)}")
        print(f"  content_type: {result.content_type}")
        if hasattr(result, 'text'):
            print(f"  text: {result.text}")
    except Exception as e:
        print(f"✗ Failed: {e}")

    # Test 5: Check ContentType enum
    print("\n--- Test 5: ContentType enum check ---")
    print(f"ContentType.TEXT.value = '{ContentType.TEXT.value}'")
    print(f"ContentType('text') = {ContentType('text')}")

    try:
        ct = ContentType("text")
        print(f"✓ ContentType('text') works: {ct}")
    except Exception as e:
        print(f"✗ ContentType('text') failed: {e}")


def test_qml_model_conversion():
    """Test QML model conversion with structured content."""

    print("\n" + "=" * 70)
    print(" QML Model Conversion Test")
    print("=" * 70)

    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
    from app.ui.chat.list.agent_chat_list_items import ChatListItem
    from agent.chat.agent_chat_message import AgentMessage

    # Create a structured content item
    text_content = TextContent(text="Hello from history!")

    # Create an AgentMessage
    agent_message = AgentMessage(
        sender_id="test_agent",
        sender_name="Test Agent",
        message_id="test-msg-1",
        structured_content=[text_content],
    )

    # Create ChatListItem
    chat_item = ChatListItem(
        message_id="test-msg-1",
        sender_id="test_agent",
        sender_name="Test Agent",
        is_user=False,
        agent_message=agent_message,
    )

    print(f"\nChatListItem created:")
    print(f"  message_id: {chat_item.message_id}")
    print(f"  sender_name: {chat_item.sender_name}")
    print(f"  agent_message.structured_content: {chat_item.agent_message.structured_content}")

    # Convert to QML format
    print(f"\nConverting to QML format...")
    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    print(f"\nQML item:")
    print(f"  messageId: {qml_item.get('messageId')}")
    print(f"  senderName: {qml_item.get('senderName')}")
    print(f"  structuredContent: {qml_item.get('structuredContent')}")

    # Check structured content format
    structured_content = qml_item.get('structuredContent', [])
    if structured_content:
        print(f"\nFirst structured content item:")
        print(f"  {json.dumps(structured_content[0], indent=2)}")


def test_serialize_deserialize():
    """Test serialize -> deserialize round trip."""

    print("\n" + "=" * 70)
    print(" Serialize -> Deserialize Round Trip Test")
    print("=" * 70)

    # Create original content
    original = TextContent(text="Round trip test")

    print(f"\n1. Original:")
    print(f"   Type: {type(original)}")
    print(f"   text: {original.text}")

    # Serialize
    serialized = original.to_dict()
    print(f"\n2. Serialized (to_dict()):")
    print(f"   {json.dumps(serialized, indent=2)}")

    # Deserialize
    try:
        deserialized = TextContent.from_dict(serialized)
        print(f"\n3. Deserialized (from_dict()):")
        print(f"   Type: {type(deserialized)}")
        print(f"   text: {deserialized.text}")

        if deserialized.text == original.text:
            print(f"\n✓ Round trip successful!")
        else:
            print(f"\n✗ Round trip failed: text mismatch")
    except Exception as e:
        print(f"\n✗ Deserialization failed: {e}")


if __name__ == "__main__":
    test_structure_content_from_dict()
    test_qml_model_conversion()
    test_serialize_deserialize()
    print("\n" + "=" * 70)
    print(" Tests completed")
    print("=" * 70)
