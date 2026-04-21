"""Debug test to capture QML errors and check component loading."""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QTextEdit
from PySide6.QtCore import QTimer, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QUrl

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class QMLDebugWindow(QMainWindow):
    """Debug window to check QML loading."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("QML Debug Test")
        self.setGeometry(100, 100, 1200, 700)

        self._setup_ui()
        QTimer.singleShot(1000, self._load_qml)

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # QML view
        self.qml_view = QQuickWidget()
        self.qml_view.setResizeMode(QQuickWidget.SizeRootObjectToView)
        layout.addWidget(self.qml_view)

        # Debug output
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setMaximumHeight(200)
        layout.addWidget(self.debug_text)

        self._log("QML Debug Test Started")
        self._log(f"Project root: {project_root}")

    def _log(self, msg):
        self.debug_text.append(msg)
        print(msg)

    def _load_qml(self):
        # Get QML path
        qml_path = project_root / "app/ui/chat/qml/AgentChatList.qml"
        self._log(f"Loading QML: {qml_path}")
        self._log(f"File exists: {qml_path.exists()}")

        # Set context properties
        self._log("Setting context properties...")
        # Create a dummy model
        from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
        dummy_model = QmlAgentChatListModel()
        self.qml_view.rootContext().setContextProperty("_chatModel", dummy_model)
        self._log("✓ Set _chatModel")

        # Load QML
        self._log("Loading QML file...")
        self.qml_view.setSource(QUrl.fromLocalFile(str(qml_path)))

        # Check for errors
        status = self.qml_view.status()
        self._log(f"QML Status: {status}")

        if status == QQuickWidget.Error:
            errors = self.qml_view.errors()
            self._log(f"✗ QML Errors ({len(errors)}):")
            for error in errors:
                self._log(f"  - {error.toString()}")
        elif status == QQuickWidget.Ready:
            self._log("✓ QML loaded successfully")

            # Get root object
            root = self.qml_view.rootObject()
            if root:
                self._log(f"✓ Root object: {root}")
                self._log(f"  Type: {type(root)}")
            else:
                self._log("✗ No root object")

        # Check UserMessageBubble.qml
        self._log("\n" + "=" * 50)
        self._log("Checking UserMessageBubble.qml...")
        user_bubble_path = project_root / "app/ui/chat/qml/components/UserMessageBubble.qml"
        self._log(f"Path: {user_bubble_path}")
        self._log(f"Exists: {user_bubble_path.exists()}")

        # Read and check syntax
        try:
            content = user_bubble_path.read_text()
            self._log(f"File size: {len(content)} bytes")
            self._log(f"Lines: {len(content.splitlines())}")

            # Check for key properties
            checks = {
                "userName": "userName" in content,
                "userIcon": "userIcon" in content,
                "structuredContent": "structuredContent" in content,
                "contentText": "contentText" in content,
            }

            self._log("Property checks:")
            for prop, found in checks.items():
                status = "✓" if found else "✗"
                self._log(f"  {status} {prop}: {found}")

        except Exception as e:
            self._log(f"✗ Error reading file: {e}")


def main():
    app = QApplication(sys.argv)
    window = QMLDebugWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
