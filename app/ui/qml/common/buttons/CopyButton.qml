// CopyButton.qml - Specialized button for copy-to-clipboard actions
// Shows "Copy" text, changes to checkmark on success

import QtQuick 2.15
import ".."

GhostButton {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // The text to copy (if empty, copies from clipboardSource)
    property string textToCopy: ""

    // Alternative: bind a TextEdit to copy from
    property var clipboardSource: null

    // Reset delay after successful copy (ms)
    property int resetDelay: 2000

    // Signals
    signal copyCompleted()

    // ─────────────────────────────────────────────────────────────
    // Internal State
    // ─────────────────────────────────────────────────────────────
    property bool _copied: false

    // ─────────────────────────────────────────────────────────────
    // Button Configuration
    // ─────────────────────────────────────────────────────────────
    iconText: _copied ? "✓" : "📋"
    text: _copied ? "" : qsTr("Copy")

    // ─────────────────────────────────────────────────────────────
    // Timer to reset copied state
    // ─────────────────────────────────────────────────────────────
    Timer {
        id: resetTimer
        interval: root.resetDelay
        onTriggered: root._copied = false
    }

    // ─────────────────────────────────────────────────────────────
    // Actions
    // ─────────────────────────────────────────────────────────────
    onClicked: {
        if (clipboardSource && typeof clipboardSource.copy === "function") {
            // Copy from TextEdit
            if (clipboardSource.selectedText.length > 0) {
                clipboardSource.copy()
            } else {
                clipboardSource.selectAll()
                clipboardSource.copy()
                clipboardSource.deselect()
            }
        } else if (textToCopy !== "") {
            // Copy from string
            clipboard.setText(textToCopy)
        }

        _copied = true
        resetTimer.restart()
        copyCompleted()
    }
}
