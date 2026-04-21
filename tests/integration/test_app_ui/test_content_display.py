#!/usr/bin/env python3
"""Test AgentMessageBubble with various content types."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, QDir


def test_content_display():
    """Launch QML test interface for AgentMessageBubble content display."""

    print("\n" + "=" * 70)
    print(" AgentMessageBubble Content Display Test")
    print("=" * 70)

    # Create Qt application
    app = QApplication(sys.argv)

    # Create QML engine
    engine = QQmlApplicationEngine()

    # Add import paths for QML modules
    qml_dir = project_root / "app" / "ui" / "chat" / "qml"
    engine.addImportPath(str(qml_dir))

    # Add widgets import path
    widgets_dir = qml_dir / "widgets"
    engine.addImportPath(str(widgets_dir))

    # Add components import path
    components_dir = qml_dir / "components"
    engine.addImportPath(str(components_dir))

    print(f"\nQML import paths:")
    print(f"  - {qml_dir}")
    print(f"  - {widgets_dir}")
    print(f"  - {components_dir}")

    # Load the test QML file
    test_qml = Path(__file__).parent / "test_content_bubble.qml"
    print(f"\nLoading test QML: {test_qml}")

    engine.load(QUrl.fromLocalFile(str(test_qml)))

    if not engine.rootObjects():
        print("\n✗ Failed to load QML file!")
        return False

    print("\nTest interface launched successfully!")
    print("\nThis test displays the following content types:")
    print("  1. Simple Text")
    print("  2. Long Text (wrapping)")
    print("  3. Error")
    print("  4. Thinking")
    print("  5. Code Block")
    print("  6. Tool Call")
    print("  7. Tool Response")
    print("  8. Progress")
    print("  9. Typing Indicator")
    print(" 10. Multiple Content Types (mixed)")
    print("\nCheck each bubble to verify:")
    print("  - Content is visible and properly rendered")
    print("  - Layout is correct (no overflow)")
    print("  - Styling matches content type")
    print("  - Height is calculated correctly")

    # Run the application
    result = app.exec()

    print("\n" + "=" * 70)
    print(" Test completed")
    print("=" * 70)

    return result == 0


if __name__ == "__main__":
    try:
        success = test_content_display()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
