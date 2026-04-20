#!/usr/bin/env python3
"""Compare data formats between test interface and history loading."""

import sys
import os
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def test_manual_data_format():
    """Test data format like test_content_bubble_debug.qml"""
    print("\n" + "=" * 70)
    print(" Test 1: Manual Data Format (like test_content_bubble_debug.qml)")
    print("=" * 70)

    from agent.chat.content import TextContent

    # Create test content like in QML test
    test_data = {
        "content_type": "text",
        "data": {"text": "Hello World"}
    }

    print(f"\nInput data (from QML test):")
    print(json.dumps(test_data, indent=2, ensure_ascii=False))

    # Parse it
    content = TextContent.from_dict(test_data)

    print(f"\nParsed TextContent:")
    print(f"  text: '{content.text}'")
    print(f"  content_type: {content.content_type}")

    # Convert back to dict
    serialized = content.to_dict()
    print(f"\nSerialized back to dict:")
    print(json.dumps(serialized, indent=2, ensure_ascii=False))

    return serialized


def test_history_data_format():
    """Test data format from actual history"""
    print("\n" + "=" * 70)
    print(" Test 2: History Data Format")
    print("=" * 70)

    from agent.chat.content import TextContent
    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

    # Get history
    workspace_path = os.path.expanduser("~/.filmeto_workspace")
    if not os.path.exists(workspace_path):
        workspace_path = os.path.join(project_root, "workspace")

    projects_dir = os.path.join(workspace_path, "projects")
    if not os.path.exists(projects_dir):
        print("[WARNING] Projects directory not found")
        return None

    project_names = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
    if not project_names:
        print("[WARNING] No projects found")
        return None

    project_name = project_names[0]
    history = FastMessageHistoryService.get_history(workspace_path, project_name)
    messages = history.get_latest_messages(count=5)

    if not messages:
        print("[WARNING] No messages found")
        return None

    # Find a message with text content
    for msg in messages:
        structured_content = msg.get('structured_content', [])
        if not structured_content:
            continue

        for item in structured_content:
            if isinstance(item, dict) and item.get('content_type') == 'text':
                print(f"\nFound text content from history:")
                print(json.dumps(item, indent=2, ensure_ascii=False))

                # Parse it
                content = TextContent.from_dict(item)
                print(f"\nParsed TextContent:")
                print(f"  text: '{content.text}'")
                print(f"  content_type: {content.content_type}")

                # Convert back to dict
                serialized = content.to_dict()
                print(f"\nSerialized back to dict:")
                print(json.dumps(serialized, indent=2, ensure_ascii=False))

                return item, serialized

    print("[WARNING] No text content found in history")
    return None


def test_qml_model_conversion():
    """Test conversion to QML model format"""
    print("\n" + "=" * 70)
    print(" Test 3: QML Model Conversion")
    print("=" * 70)

    from agent.chat.content import TextContent
    from agent.chat.agent_chat_types import ContentType
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
    from app.ui.chat.list.agent_chat_list_items import ChatListItem
    from agent import AgentMessage

    # Create a TextContent
    text_content = TextContent(text="Test message")

    # Create an AgentMessage
    agent_message = AgentMessage(
        sender_id="test",
        sender_name="Test Agent",
        message_id="test-123",
        structured_content=[text_content],
    )

    # Create a ChatListItem
    chat_item = ChatListItem(
        message_id="test-123",
        sender_id="test",
        sender_name="Test Agent",
        is_user=False,
        agent_message=agent_message,
    )

    # Convert to QML format
    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    print(f"\nQML item structuredContent:")
    if qml_item.get('structuredContent'):
        sc = qml_item['structuredContent'][0]
        print(json.dumps(sc, indent=2, ensure_ascii=False))
        print(f"\nContent type: {sc.get('content_type')}")
        print(f"Has 'data' key: {'data' in sc}")
        if 'data' in sc:
            print(f"Data type: {type(sc['data'])}")
            print(f"Data keys: {list(sc['data'].keys()) if isinstance(sc['data'], dict) else 'N/A'}")
            print(f"Text value: {sc['data'].get('text', 'MISSING') if isinstance(sc['data'], dict) else 'NOT A DICT'}")
    else:
        print("  No structuredContent!")

    return qml_item


if __name__ == "__main__":
    try:
        # Test 1: Manual format
        manual_serialized = test_manual_data_format()

        # Test 2: History format
        history_result = test_history_data_format()

        # Test 3: QML model conversion
        qml_item = test_qml_model_conversion()

        # Compare
        if history_result:
            history_item, history_serialized = history_result
            print("\n" + "=" * 70)
            print(" Comparison: Manual vs History")
            print("=" * 70)
            print(f"\nManual format (from QML test):")
            print(json.dumps(manual_serialized, indent=2, ensure_ascii=False))
            print(f"\nHistory format (from storage):")
            print(json.dumps(history_serialized, indent=2, ensure_ascii=False))

            print(f"\n\nKeys comparison:")
            manual_keys = set(manual_serialized.keys())
            history_keys = set(history_serialized.keys())
            print(f"  Manual keys: {sorted(manual_keys)}")
            print(f"  History keys: {sorted(history_keys)}")
            print(f"  Difference: {manual_keys.symmetric_difference(history_keys)}")

        sys.exit(0)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
