"""
Test the actual agent_chat QML integration scenario.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PySide6.QtCore import QUrl, QTimer, Slot

print("=" * 70)
print("Agent Chat QML Integration Test")
print("=" * 70)

app = QApplication.instance() or QApplication(sys.argv)

# Import after app creation
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from agent.chat.content import TextContent, ThinkingContent, ProgressContent, ToolCallContent

# Test with actual workspace setup
from app.data.workspace import Workspace

print("\nLoading workspace...")
workspace = Workspace(str(project_root / "workspace"))
project_name = "demo"

print(f"Workspace path: {workspace.workspace_path}")
print(f"Project name: {project_name}")

# Create the widget
print("\nCreating QmlAgentChatListWidget...")
widget = QmlAgentChatListWidget(workspace)

print(f"QML root object: {widget._qml_root}")
print(f"Model row count: {widget._model.rowCount()}")

# Create a test window
test_window = QWidget()
test_window.setWindowTitle("Agent Chat QML Integration Test")
test_window.resize(800, 600)

layout = QVBoxLayout(test_window)

# Add info label
info_label = QLabel("QML Integration Test")
info_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
layout.addWidget(info_label)

# Add status text
status_text = QTextEdit()
status_text.setReadOnly(True)
status_text.setMaximumHeight(150)
layout.addWidget(status_text)

# Add the chat widget
layout.addWidget(widget)

# Add test buttons
button_layout = QVBoxLayout()

def add_test_message():
    """Add a test message to verify data flow."""
    status_text.clear()

    try:
        from agent.chat.agent_chat_message import AgentMessage
        import uuid

        # Create a test agent message with various content types
        message_id = str(uuid.uuid4())

        message = AgentMessage(
            sender_id="test_agent",
            sender_name="测试助手",
            message_id=message_id,
            metadata={"timestamp": "2026-02-08T15:30:00"},
            structured_content=[
                TextContent(text="你好！让我来帮你分析这个问题。"),
                ThinkingContent(thought="首先，我需要理解用户的具体需求..."),
                ToolCallContent(tool_name="search_files", tool_args={"pattern": "*.py", "path": "/src"}),
                ProgressContent(progress="正在搜索文件...", percentage=50),
                TextContent(text="找到了 5 个相关的 Python 文件。"),
            ],
        )

        status_text.append("Creating AgentMessage...")
        status_text.append(f"  Message ID: {message_id}")
        status_text.append(f"  Sender: {message.sender_name}")
        status_text.append(f"  Content items: {len(message.structured_content)}")

        for i, content in enumerate(message.structured_content):
            status_text.append(f"    [{i}] {content.content_type.value}")

        # Convert to QML format
        qml_item = QmlAgentChatListModel.from_agent_message(
            message,
            agent_color="#4a90e2",
            agent_icon="🤖",
            crew_metadata={}
        )

        status_text.append("\nConverting to QML format...")
        status_text.append(f"  contentType: {qml_item[QmlAgentChatListModel.CONTENT_TYPE]}")

        structured_content = qml_item[QmlAgentChatListModel.STRUCTURED_CONTENT]
        status_text.append(f"  structuredContent items: {len(structured_content)}")

        for i, sc in enumerate(structured_content):
            ct = sc.get('content_type')
            status_text.append(f"    [{i}] {ct}")

        # Add to model
        widget._model.add_item(qml_item)
        status_text.append(f"\nAdded to model!")
        status_text.append(f"Model row count: {widget._model.rowCount()}")

        # Verify item was added
        item = widget._model.get_item(widget._model.rowCount() - 1)
        if item:
            status_text.append(f"\nVerifying last item in model:")
            status_text.append(f"  messageId: {item.get(QmlAgentChatListModel.MESSAGE_ID)}")
            status_text.append(f"  senderName: {item.get(QmlAgentChatListModel.SENDER_NAME)}")
            status_text.append(f"  structuredContent: {len(item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, []))} items")

        # Force QML refresh
        widget._refresh_qml_model()
        status_text.append("\nQML model refreshed!")

        status_text.append("\n✓ Test message added successfully!")
        status_text.append("Check the QML view to see if the message is displayed.")

    except Exception as e:
        status_text.append(f"\n✗ Error: {e}")
        import traceback
        status_text.append(traceback.format_exc())

def clear_model():
    """Clear the model to test fresh state."""
    widget._model.clear()
    status_text.clear()
    status_text.append("Model cleared!")
    status_text.append(f"Row count: {widget._model.rowCount()}")

def show_model_state():
    """Show current model state."""
    status_text.clear()
    status_text.append(f"Model row count: {widget._model.rowCount()}")

    for i in range(widget._model.rowCount()):
        item = widget._model.get_item(i)
        sender_name = item.get(QmlAgentChatListModel.SENDER_NAME, "Unknown")
        content_type = item.get(QmlAgentChatListModel.CONTENT_TYPE, "unknown")
        sc_count = len(item.get(QmlAgentChatListModel.STRUCTURED_CONTENT, []))
        status_text.append(f"  [{i}] {sender_name} - {content_type} ({sc_count} content items)")

add_btn = QPushButton("Add Test Message")
add_btn.clicked.connect(add_test_message)
button_layout.addWidget(add_btn)

clear_btn = QPushButton("Clear Model")
clear_btn.clicked.connect(clear_model)
button_layout.addWidget(clear_btn)

state_btn = QPushButton("Show Model State")
state_btn.clicked.connect(show_model_state)
button_layout.addWidget(state_btn)

layout.addLayout(button_layout)

test_window.show()

print("\n" + "=" * 70)
print("Test Window Launched")
print("=" * 70)
print("""
Instructions:
1. Click 'Add Test Message' to add a message with multiple content types
2. Check the QML view above to see if content is displayed
3. If content is not visible, check for:
   - QML errors in console
   - Model state using 'Show Model State' button
4. Click 'Clear Model' to reset and test again

Expected behavior:
- Message should appear with sender name "测试助手"
- Content should show:
  1. Text: "你好！让我来帮你分析这个问题。"
  2. Thinking: "首先，我需要理解用户的具体需求..."
  3. Tool Call: search_files
  4. Progress: "正在搜索文件..."
  5. Text: "找到了 5 个相关的 Python 文件。"
""")

# Check initial state
QTimer.singleShot(100, show_model_state)

result = app.exec()

print("\nTest completed!")
sys.exit(0 if result == 0 else 1)
