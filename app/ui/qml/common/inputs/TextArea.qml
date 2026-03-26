// TextArea.qml - Styled multi-line text input
// Use for multi-line text input

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

TextArea {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Error state
    property bool hasError: false
    property string errorMessage: ""

    // Whether to show border
    property bool showBorder: true

    // ─────────────────────────────────────────────────────────────
    // Internal Properties
    // ─────────────────────────────────────────────────────────────
    readonly property color _borderColor: {
        if (hasError) return Theme.error
        if (activeFocus) return Theme.borderFocus
        if (hovered) return Theme.borderHover
        return Theme.border
    }

    // ─────────────────────────────────────────────────────────────
    // Field Configuration
    // ─────────────────────────────────────────────────────────────
    selectByMouse: true
    wrapMode: TextEdit.Wrap

    // ─────────────────────────────────────────────────────────────
    // Colors
    // ─────────────────────────────────────────────────────────────
    color: Theme.textPrimary
    placeholderTextColor: Theme.textTertiary
    selectionColor: Theme.accent
    selectedTextColor: "white"

    // ─────────────────────────────────────────────────────────────
    // Background
    // ─────────────────────────────────────────────────────────────
    background: Rectangle {
        radius: Theme.radiusSmall

        color: Theme.inputBackground
        border.color: root.showBorder ? root._borderColor : "transparent"
        border.width: root.showBorder ? 1 : 0

        Behavior on border.color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Font & Padding
    // ─────────────────────────────────────────────────────────────
    font.pixelSize: Theme.fontMedium
    leftPadding: 12
    rightPadding: 12
    topPadding: 8
    bottomPadding: 8
}
