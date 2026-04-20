#!/usr/bin/env python3
"""验证修复后的 QML 模型数据访问"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl


def test_fixed_model_access():
    """测试修复后的 model.<role> 访问方式"""

    print("\n" + "=" * 70)
    print(" 验证修复：model.<role> 数据访问")
    print("=" * 70)

    # 准备测试数据
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
    history = FastMessageHistoryService.get_history(workspace_path, project_name)
    messages = history.get_latest_messages(count=1)

    if not messages:
        print("[WARNING] No messages found")
        return False

    msg_data = messages[0]
    metadata = msg_data.get("metadata", {})
    content_list = msg_data.get("structured_content") or msg_data.get("content", [])
    if not content_list:
        content_list = metadata.get("structured_content") or metadata.get("content", [])

    # 解析内容
    structured_content = []
    for content_item in content_list:
        if isinstance(content_item, dict):
            try:
                sc = StructureContent.from_dict(content_item)
                structured_content.append(sc)
            except Exception as e:
                print(f"[WARNING] Failed to parse content: {e}")

    if not structured_content:
        print("[WARNING] No structured content")
        return False

    # 创建 QML 模型项
    message_id = msg_data.get("message_id") or metadata.get("message_id", "")
    sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
    sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)

    agent_message = AgentMessage(
        sender_id=sender_id,
        sender_name=sender_name,
        message_id=message_id,
        structured_content=structured_content,
    )

    chat_item = ChatListItem(
        message_id=message_id,
        sender_id=sender_id,
        sender_name=sender_name,
        is_user=False,
        agent_message=agent_message,
    )

    qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

    # 创建模型
    model = QmlAgentChatListModel()
    model.add_item(qml_item)

    print(f"[INFO] Model created with {model.rowCount()} items")

    # 创建 QML 应用
    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # 添加导入路径
    qml_dir = project_root / "app" / "ui" / "chat" / "qml"
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "widgets"))
    engine.addImportPath(str(qml_dir / "components"))

    # 暴露模型给 QML
    engine.rootContext().setContextProperty("_chatModel", model)

    # 创建测试 QML - 使用修复后的 model.<role> 语法
    test_qml = f"""
import QtQuick 2.15
import QtQuick.Controls 2.15
import "file://{qml_dir}/components" as Components

ApplicationWindow {{
    visible: true
    width: 800
    height: 600
    title: "Fixed Model Access Test"

    color: "#1e1e1e"

    Column {{
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {{
            text: "Fixed: model.<role> Access Test"
            color: "#ffffff"
            font.pixelSize: 18
            font.weight: Font.Bold
        }}

        Text {{
            text: "Model row count: " + _chatModel.rowCount()
            color: "#aaaaaa"
            font.pixelSize: 12
        }}

        Rectangle {{
            width: parent.width
            height: 300
            color: "#252525"
            border.color: "#444"
            border.width: 1

            ListView {{
                anchors.fill: parent
                anchors.margins: 10
                model: _chatModel
                spacing: 10

                delegate: Components.AgentMessageBubble {{
                    width: parent.width
                    senderName: model.senderName || ""
                    agentColor: model.agentColor || "#4a90e2"
                    agentIcon: model.agentIcon || "🤖"
                    structuredContent: model.structuredContent || []
                    timestamp: ""
                    crewMetadata: {{}}

                    Component.onCompleted: {{
                        console.log("[QML Fixed] AgentMessageBubble loaded")
                        console.log("[QML Fixed] model.senderName:", model.senderName)
                        console.log("[QML Fixed] model.structuredContent:", JSON.stringify(model.structuredContent))
                        if (model.structuredContent && model.structuredContent.length > 0) {{
                            console.log("[QML Fixed] First item:", JSON.stringify(model.structuredContent[0]))
                        }}
                    }}
                }}
            }}
        }}
    }}
}}
"""

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.qml', delete=False) as f:
        f.write(test_qml)
        test_qml_path = f.name

    print(f"\nLoading test QML: {test_qml_path}")

    engine.load(QUrl.fromLocalFile(test_qml_path))

    if not engine.rootObjects():
        print("\n✗ Failed to load QML!")
        return False

    print("\nQML loaded successfully!")
    print("\nThis test uses the FIXED syntax: model.senderName, model.structuredContent")
    print("Text should now be visible in the message bubble.")
    print("\nCheck console output for detailed logs.")

    result = app.exec()

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
        success = test_fixed_model_access()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
