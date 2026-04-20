"""
Diagnose QML import path differences between QQmlApplicationEngine and QQuickWidget.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import QUrl, QObject, Signal
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickWidgets import QQuickWidget

print("=" * 70)
print("QML Import Path Diagnosis")
print("=" * 70)

app = QApplication.instance() or QApplication(sys.argv)

qml_dir = project_root / "app" / "ui" / "chat" / "qml"
widgets_dir = qml_dir / "widgets"
components_dir = qml_dir / "components"

print(f"\nDirectory structure:")
print(f"  qml_dir: {qml_dir}")
print(f"    exists: {qml_dir.exists()}")
print(f"  widgets_dir: {widgets_dir}")
print(f"    exists: {widgets_dir.exists()}")
print(f"  components_dir: {components_dir}")
print(f"    exists: {components_dir.exists()}")

print(f"\nComponents directory contents:")
if components_dir.exists():
    for f in components_dir.glob("*.qml"):
        print(f"  - {f.name}")

print(f"\nWidgets directory contents:")
if widgets_dir.exists():
    for f in widgets_dir.glob("*.qml"):
        print(f"  - {f.name}")

# Test 1: QQmlApplicationEngine with import paths
print("\n" + "=" * 70)
print("Test 1: QQmlApplicationEngine with import paths")
print("=" * 70)

engine = QQmlApplicationEngine()
engine.addImportPath(str(qml_dir))
engine.addImportPath(str(widgets_dir))
engine.addImportPath(str(components_dir))

test_qml_1 = project_root / "tests" / "test_app" / "test_ui" / "test_content_bubble.qml"
print(f"Loading: {test_qml_1}")
engine.load(QUrl.fromLocalFile(str(test_qml_1)))

if engine.rootObjects():
    print("✓ QQmlApplicationEngine loaded successfully")
else:
    print("✗ QQmlApplicationEngine failed to load")
    # Check for errors
    print("Note: This test requires GUI to verify visual output")

# Test 2: QQuickWidget without explicit import paths
print("\n" + "=" * 70)
print("Test 2: QQuickWidget without explicit import paths")
print("=" * 70)

widget = QQuickWidget()
agent_chat_qml = qml_dir / "AgentChatList.qml"
print(f"Loading: {agent_chat_qml}")

widget.setSource(QUrl.fromLocalFile(str(agent_chat_qml)))

if widget.status() == QQuickWidget.Error:
    print("✗ QQuickWidget failed to load")
    errors = widget.errors()
    for error in errors:
        print(f"  Error: {error.toString()}")
elif widget.status() == QQuickWidget.Null:
    print("✗ QQuickWidget status is Null")
else:
    print("✓ QQuickWidget loaded successfully")
    root = widget.rootObject()
    if root:
        print(f"  Root object type: {root.metaObject().className()}")
    else:
        print("  No root object")

# Test 3: QQuickWidget with import paths
print("\n" + "=" * 70)
print("Test 3: QQuickWidget with import paths")
print("=" * 70)

widget2 = QQuickWidget()

# Try setting import paths on the engine (not directly available on QQuickWidget)
# We need to access the underlying engine
from PySide6.QtQuick import QQuickEngine

# Note: QQuickWidget doesn't expose the engine directly for import path manipulation
# But we can try using a workaround with QQmlEngine

print("Note: QQuickWidget doesn't directly expose import path configuration")
print("The widget should resolve relative paths from the QML file location")

# Let's check what the QML file imports
print("\nChecking QML import statements:")
agent_chat_content = (qml_dir / "AgentChatList.qml").read_text()
for line in agent_chat_content.split('\n')[:20]:
    if 'import' in line.lower():
        print(f"  {line.strip()}")

# Test 4: Check relative path resolution
print("\n" + "=" * 70)
print("Test 4: Relative Path Resolution")
print("=" * 70)

print(f"\nAgentChatList.qml location: {agent_chat_qml}")
print(f"Expected components path (relative): ./components")
print(f"Absolute components path: {components_dir}")

resolved = (agent_chat_qml.parent / "components").resolve()
print(f"Resolved path: {resolved}")
print(f"Exists: {resolved.exists()}")

print("\n" + "=" * 70)
print("Diagnosis Complete")
print("=" * 70)
print("""
Summary:
- QQmlApplicationEngine works with explicit import paths
- QQuickWidget should resolve relative paths automatically
- If QQuickWidget fails, it may be due to:
  1. Path resolution issues
  2. Missing QML import plugins
  3. QML syntax errors in components
""")
