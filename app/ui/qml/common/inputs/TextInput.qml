// TextInput.qml - Styled text input field
// Use for single-line text input

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

TextField {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Size variant
    property string size: "medium"  // "small", "medium", "large"

    // Field type affects styling
    property string fieldType: "text"  // "text", "password", "url", "email"

    // Error state
    property bool hasError: false
    property string errorMessage: ""

    // ─────────────────────────────────────────────────────────────
    // Internal Properties
    // ─────────────────────────────────────────────────────────────
    readonly property int _inputHeight: {
        switch(size) {
            case "small": return 24
            case "large": return 40
            default: return Theme.inputHeight
        }
    }

    readonly property color _borderColor: {
        if (hasError) return Theme.error
        if (activeFocus) return Theme.borderFocus
        if (hovered) return Theme.borderHover
        return Theme.border
    }

    // ─────────────────────────────────────────────────────────────
    // Field Configuration
    // ─────────────────────────────────────────────────────────────
    implicitHeight: _inputHeight
    selectByMouse: true

    echoMode: fieldType === "password" ? TextField.Password : TextField.Normal

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
        border.color: root._borderColor
        border.width: 1

        Behavior on border.color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Font
    // ─────────────────────────────────────────────────────────────
    font.pixelSize: Theme.fontMedium
    leftPadding: 12
    rightPadding: 12
    verticalAlignment: Text.AlignVCenter
}
