#!/usr/bin/env python3
"""Simulate the complete startup window flow to find where data gets lost."""

import sys
import os
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def simulate_history_loading():
    """Simulate loading history data like startup window does."""
    print("\n" + "=" * 70)
    print(" Step 1: Load History Data")
    print("=" * 70)

    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

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
    print(f"[INFO] Using project: {project_name}")

    history = FastMessageHistoryService.get_history(workspace_path, project_name)
    messages = history.get_latest_messages(count=3)

    print(f"[INFO] Loaded {len(messages)} messages")

    return messages


def simulate_build_item(msg_data):
    """Simulate _build_item_from_history process."""
    print("\n" + "=" * 70)
    print(" Step 2: Build ChatListItem")
    print("=" * 70)

    from agent.chat.content import StructureContent
    from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget

    metadata = msg_data.get("metadata", {})
    content_list = msg_data.get("structured_content") or msg_data.get("content", [])
    if not content_list:
        content_list = metadata.get("structured_content") or metadata.get("content", [])

    message_id = msg_data.get("message_id") or metadata.get("message_id", "")
    sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
    sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)

    print(f"[DEBUG] Parsing message: {message_id[:8]}... from {sender_name}")
    print(f"[DEBUG] content_list length: {len(content_list)}")
    print(f"[DEBUG] First content item:")
    if content_list:
        print(json.dumps(content_list[0], indent=2, ensure_ascii=False))

    # Parse structured content
    structured_content = []
    for i, content_item in enumerate(content_list):
        if isinstance(content_item, dict):
            try:
                sc = StructureContent.from_dict(content_item)
                structured_content.append(sc)
                print(f"[DEBUG]   Parsed content[{i}]: {type(sc).__name__} - content_type={sc.content_type}")
                if hasattr(sc, 'text'):
                    print(f"[DEBUG]     text: {sc.text[:50]}...")
            except Exception as e:
                print(f"[WARNING] Failed to load structured content[{i}]: {e}")

    return structured_content, sender_name, message_id


def simulate_qml_conversion(structured_content, sender_name, message_id):
    """Simulate QML model conversion."""
    print("\n" + "=" * 70)
    print(" Step 3: Convert to QML Format")
    print("=" * 70)

    from agent import AgentMessage
    from app.ui.chat.list.agent_chat_list_items import ChatListItem
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

    # Create AgentMessage
    agent_message = AgentMessage(
        sender_id="test",
        sender_name=sender_name,
        message_id=message_id,
        structured_content=structured_content,
    )

    # Create ChatListItem
    chat_item = ChatListItem(
        message_id=message_id,
        sender_id="test",
        sender_name=sender_name,
        is_user=False,
        agent_message=agent_message,
    )

    # Convert to QML format
    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    print(f"[DEBUG] QML item structuredContent length: {len(qml_item.get('structuredContent', []))}")
    if qml_item.get('structuredContent'):
        print(f"[DEBUG] First item:")
        print(json.dumps(qml_item['structuredContent'][0], indent=2, ensure_ascii=False))

    return qml_item


def simulate_qml_widget(qml_item):
    """Simulate QML widget rendering."""
    print("\n" + "=" * 70)
    print(" Step 4: Simulate QML Widget")
    print("=" * 70)

    structuredContent = qml_item.get('structuredContent', [])
    if not structuredContent:
        print("[WARNING] No structuredContent in QML item!")
        return

    # Simulate what AgentMessageBubble.qml does
    for i, modelData in enumerate(structuredContent):
        print(f"\n[QML Simulation] Processing content item {i}:")
        print(f"  modelData keys: {list(modelData.keys())}")
        print(f"  content_type: {modelData.get('content_type')}")

        # This is what the Loader does
        content_type = modelData.get('content_type') or modelData.get('type', 'text')

        # Simulate setting item.data
        widget_data = modelData

        # This is what TextWidget.safeGet does
        def safe_get(data, prop, default=""):
            if not data:
                return default
            if data.get(prop) is not None:
                return data.get(prop)
            if isinstance(data.get('data'), dict):
                return data.get('data', {}).get(prop, default)
            return default

        # Try to extract text (like TextWidget does)
        text = safe_get(widget_data, "text", "")
        print(f"  Extracted text: '{text}'")

        if not text:
            # Try nested extraction
            data_dict = widget_data.get('data', {})
            if isinstance(data_dict, dict):
                text = data_dict.get('text', '')
                print(f"  Extracted from data.text: '{text}'")

        if not text:
            print(f"  [ERROR] Failed to extract text!")
            print(f"  widget_data: {json.dumps(widget_data, indent=4, ensure_ascii=False)}")


if __name__ == "__main__":
    try:
        # Step 1: Load history
        messages = simulate_history_loading()
        if not messages:
            sys.exit(1)

        # Find a text message
        text_msg = None
        for msg in messages:
            sc = msg.get('structured_content', [])
            if sc and sc[0].get('content_type') == 'text':
                text_msg = msg
                break

        if not text_msg:
            print("[WARNING] No text message found")
            sys.exit(1)

        # Step 2: Build item
        structured_content, sender_name, message_id = simulate_build_item(text_msg)

        # Step 3: Convert to QML
        qml_item = simulate_qml_conversion(structured_content, sender_name, message_id)

        # Step 4: Simulate QML widget
        simulate_qml_widget(qml_item)

        print("\n" + "=" * 70)
        print(" Simulation Complete")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
