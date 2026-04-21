#!/usr/bin/env python3
"""Debug test for AgentMessageBubble text content display."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl


def test_text_content_debug():
    """Launch simplified debug test for text content."""

    print("\n" + "=" * 70)
    print(" AgentMessageBubble Text Content Debug Test")
    print("=" * 70)

    app = QApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Add import paths
    qml_dir = project_root / "app" / "ui" / "chat" / "qml"
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "widgets"))
    engine.addImportPath(str(qml_dir / "components"))

    print(f"\nQML import paths added:")
    print(f"  - {qml_dir}")

    # Load debug test
    test_qml = Path(__file__).parent / "test_content_bubble_debug.qml"
    print(f"\nLoading: {test_qml}")

    engine.load(QUrl.fromLocalFile(str(test_qml)))

    if not engine.rootObjects():
        print("\n✗ Failed to load QML!")
        return False

    print("\nDebug test launched!")
    print("\nThis test shows 3 scenarios:")
    print("  1. Minimal text data structure")
    print("  2. Full text data structure")
    print("  3. Multiple content items (text + error)")
    print("\nCheck if text is visible in each bubble.")
    print("If text is NOT visible, the issue is confirmed.")

    result = app.exec()

    print("\n" + "=" * 70)
    print(" Test completed")
    print("=" * 70)

    return result == 0


if __name__ == "__main__":
    try:
        success = test_text_content_debug()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
