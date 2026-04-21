#!/usr/bin/env python3
"""Test QML AgentChatList directly with real history data."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, QObject, Signal, Property, Slot


class HistoryDataBridge(QObject):
    """Bridge to provide history data to QML."""

    dataChanged = Signal()

    def __init__(self):
        super().__init__()
        self._data = []

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data
        self.dataChanged.emit()

    data = Property('QVariant', get_data, notify=dataChanged)


def test_qml_with_real_history():
    """Test QML AgentChatList with real history data."""

    print("\n" + "=" * 70)
    print(" QML AgentChatList with Real History Data")
    print("=" * 70)

    # Load history data
    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
    from agent.chat.content import StructureContent
    from agent import AgentMessage
    from app.ui.chat.list.agent_chat_list_items import ChatListItem
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

    workspace_path = os.path.expanduser("~/.filmeto_workspace")
    if not os.path.exists(workspace_path):
        workspace_path = os.path.join(project_root, "workspace")

    projects_dir = os.path.join(workspace_path, "projects")
    if not os.path.exists(projects_dir):
        print("[WARNING] Projects directory not found")
        return False

    project_names = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
    if not project_names:
        print("[WARNING] No projects found")
        return False

    project_name = project_names[0]
    print(f"[INFO] Using project: {project_name}")

    history = FastMessageHistoryService.get_history(workspace_path, project_name)
    messages = history.get_latest_messages(count=3)

    print(f"[INFO] Loaded {len(messages)} messages")

    # Convert to QML format
    qml_items = []
    for msg_data in messages:
        metadata = msg_data.get("metadata", {})
        content_list = msg_data.get("structured_content") or msg_data.get("content", [])
        if not content_list:
            content_list = metadata.get("structured_content") or metadata.get("content", [])

        message_id = msg_data.get("message_id") or metadata.get("message_id", "")
        sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
        sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)

        # Parse structured content
        structured_content = []
        for content_item in content_list:
            if isinstance(content_item, dict):
                try:
                    sc = StructureContent.from_dict(content_item)
                    structured_content.append(sc)
                except Exception as e:
                    print(f"[WARNING] Failed to parse content: {e}")

        if not structured_content:
            continue

        # Create AgentMessage
        agent_message = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            message_id=message_id,
            structured_content=structured_content,
        )

        # Create ChatListItem
        chat_item = ChatListItem(
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_user=sender_id.lower() == "user",
            agent_message=agent_message,
        )

        # Convert to QML format
        qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)
        qml_items.append(qml_item)

    print(f"[INFO] Created {len(qml_items)} QML items")

    # Print first item for debugging
    if qml_items:
        print(f"\n[DEBUG] First QML item:")
        import json
        print(json.dumps(qml_items[0], indent=2, ensure_ascii=False))

    # Create QML application
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Add import paths
    qml_dir = project_root / "app" / "ui" / "chat" / "qml"
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "widgets"))
    engine.addImportPath(str(qml_dir / "components"))

    # Create bridge object
    bridge = HistoryDataBridge()
    bridge.set_data(qml_items)

    # Expose to QML
    engine.rootContext().setContextProperty("_historyData", bridge)

    print(f"\nQML import paths added:")
    print(f"  - {qml_dir}")

    # Create a simple test QML file
    test_qml_content = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import "file://{qml_dir}/components" as Components

ApplicationWindow {{
    visible: true
    width: 800
    height: 600
    title: "AgentChatList with Real History"

    color: "#1e1e1e"

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "Real History Data Test"
            color: "#ffffff"
            font.pixelSize: 18
            font.weight: Font.Bold
        }

        Text {
            text: "Messages loaded: " + _historyData.data.length
            color: "#aaaaaa"
            font.pixelSize: 12
        }

        // Test individual message bubbles
        Repeater {
            model: Math.min(3, _historyData.data.length)

            Rectangle {
                width: parent.width
                height: 200
                color: "#252525"
                border.color: "#444"
                border.width: 1

                Column {
                    anchors.fill: parent
                    anchors.margins: 10

                    Text {
                        text: "Message " + (index + 1)
                        color: "#aaa"
                        font.pixelSize: 12
                    }

                    Components.AgentMessageBubble {{
                        width: parent.width
                        senderName: _historyData.data[index].senderName
                        agentColor: _historyData.data[index].agentColor
                        agentIcon: _historyData.data[index].agentIcon
                        structuredContent: _historyData.data[index].structuredContent
                        timestamp: ""
                        crewMetadata: _historyData.data[index].crewMetadata || {{}}

                        Component.onCompleted: {
                            console.log("[QML] AgentMessageBubble loaded for message", index + 1)
                            console.log("[QML] senderName:", senderName)
                            console.log("[QML] structuredContent length:", structuredContent.length)
                            if (structuredContent.length > 0) {
                                console.log("[QML] First item:", JSON.stringify(structuredContent[0]))
                            }
                        }
                    }
                }
            }
        }
    }
}
"""

    # Write test QML to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.qml', delete=False) as f:
        f.write(test_qml_content)
        test_qml_path = f.name

    print(f"\nLoading test QML: {test_qml_path}")

    engine.load(QUrl.fromLocalFile(test_qml_path))

    if not engine.rootObjects():
        print("\n✗ Failed to load QML!")
        return False

    print("\nQML loaded successfully!")
    print("\nCheck if message text is visible in the bubbles.")
    print("If text is NOT visible, check the console output for [TextWidget] logs.")

    result = app.exec()

    # Cleanup
    try:
        os.unlink(test_qml_path)
    except:
        pass

    print("\n" + "=" * 70)
    print(" Test completed")
    print("=" * 70)

    return result == 0


if __name__ == "__main__":
    try:
        success = test_qml_with_real_history()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
