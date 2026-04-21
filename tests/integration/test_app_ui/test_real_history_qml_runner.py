#!/usr/bin/env python3
"""Run QML test for real history data format."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl


def test_qml():
    """Load and run the QML test."""

    print("\n" + "=" * 70)
    print(" Real History Data QML Test")
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

    # Load test QML
    test_qml = Path(__file__).parent / "test_real_history_qml.qml"
    print(f"\nLoading: {test_qml}")

    engine.load(QUrl.fromLocalFile(str(test_qml)))

    if not engine.rootObjects():
        print("\n✗ Failed to load QML!")
        return False

    print("\nQML loaded successfully!")
    print("\nThis test simulates the exact data format that Python passes to QML.")
    print("Check if the text '这是一条测试消息...' is visible in the bubble.")
    print("\nAlso check the console output for [TextWidget] logs.")

    result = app.exec()

    print("\n" + "=" * 70)
    print(" Test completed")
    print("=" * 70)

    return result == 0


if __name__ == "__main__":
    try:
        success = test_qml()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
