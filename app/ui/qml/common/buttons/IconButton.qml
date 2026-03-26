// IconButton.qml - Compact button with only an icon
// Use for toolbar buttons, action icons, etc.

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."

ToolButton {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Icon properties
    property string iconCode: ""          // Unicode or icon character
    property string iconFontFamily: "iconfont"
    property int iconSize: Theme.iconSize

    // Tooltip
    property string tooltip: ""

    // Size variant
    property string size: "medium"  // "small", "medium", "large"

    // Colors
    property color iconColor: Theme.textSecondary
    property color iconHoverColor: Theme.textPrimary
    property color iconPressedColor: Theme.accent
    property color iconDisabledColor: Theme.textDisabled

    // Background color on hover
    property color hoverBackgroundColor: Theme.withAlpha(Theme.textPrimary, 0.08)
    property color pressedBackgroundColor: Theme.withAlpha(Theme.textPrimary, 0.15)

    // ─────────────────────────────────────────────────────────────
    // Internal Properties
    // ─────────────────────────────────────────────────────────────
    readonly property int _buttonSize: {
        switch(size) {
            case "small": return 24
            case "large": return 36
            default: return 28
        }
    }

    readonly property int _iconPixelSize: {
        switch(size) {
            case "small": return Theme.iconSize - 2
            case "large": return Theme.iconSize + 4
            default: return Theme.iconSize
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Button Configuration
    // ─────────────────────────────────────────────────────────────
    implicitWidth: _buttonSize
    implicitHeight: _buttonSize

    font.family: iconFontFamily
    font.pixelSize: _iconPixelSize
    text: iconCode

    // ─────────────────────────────────────────────────────────────
    // Tooltip
    // ─────────────────────────────────────────────────────────────
    ToolTip.visible: hovered && tooltip !== ""
    ToolTip.text: tooltip
    ToolTip.delay: 500

    // ─────────────────────────────────────────────────────────────
    // Background
    // ─────────────────────────────────────────────────────────────
    background: Rectangle {
        radius: Theme.radiusSmall

        color: {
            if (!root.enabled) return "transparent"
            if (root.down) return pressedBackgroundColor
            if (root.hovered) return hoverBackgroundColor
            return "transparent"
        }

        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Content
    // ─────────────────────────────────────────────────────────────
    contentItem: Text {
        text: root.text
        font: root.font
        color: {
            if (!root.enabled) return iconDisabledColor
            if (root.down) return iconPressedColor
            if (root.hovered) return iconHoverColor
            return iconColor
        }

        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
