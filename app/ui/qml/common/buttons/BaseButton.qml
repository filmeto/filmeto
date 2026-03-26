// BaseButton.qml - Base button component with common styling
// Extend this for specific button variants

import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."  // For Theme

Button {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Size variants
    property string size: "medium"  // "small", "medium", "large"

    // Whether button should expand to fill width
    property bool fullWidth: false

    // Custom colors (override defaults)
    property color backgroundColor: Theme.accent
    property color backgroundHoverColor: Theme.accentHover
    property color backgroundPressedColor: Theme.accentPressed
    property color backgroundDisabledColor: Theme.border
    property color textColor: "white"
    property color textDisabledColor: Theme.textDisabled

    // Icon support
    property string iconText: ""
    property string iconFont: ""
    property int iconSize: Theme.iconSize

    // ─────────────────────────────────────────────────────────────
    // Internal Properties
    // ─────────────────────────────────────────────────────────────
    readonly property int _buttonHeight: {
        switch(size) {
            case "small": return Theme.buttonHeightSmall
            case "large": return Theme.buttonHeightLarge
            default: return Theme.buttonHeight
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Button Configuration
    // ─────────────────────────────────────────────────────────────
    implicitHeight: _buttonHeight
    implicitWidth: fullWidth ? parent.width : Math.max(implicitContentWidth + 24, 80)

    // ─────────────────────────────────────────────────────────────
    // Background
    // ─────────────────────────────────────────────────────────────
    background: Rectangle {
        radius: Theme.radiusMedium

        color: {
            if (!root.enabled) return backgroundDisabledColor
            if (root.down) return backgroundPressedColor
            if (root.hovered) return backgroundHoverColor
            return backgroundColor
        }

        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Content
    // ─────────────────────────────────────────────────────────────
    contentItem: Row {
        spacing: root.iconText !== "" ? 6 : 0
        leftPadding: 12
        rightPadding: 12

        anchors.centerIn: parent

        // Icon
        Text {
            visible: root.iconText !== ""
            text: root.iconText
            font.family: root.iconFont || "iconfont"
            font.pixelSize: root.iconSize
            color: root.enabled ? root.textColor : root.textDisabledColor
            anchors.verticalCenter: parent.verticalCenter
        }

        // Text
        Text {
            text: root.text
            font.pixelSize: Theme.fontMedium
            font.bold: size !== "small"
            color: root.enabled ? root.textColor : root.textDisabledColor
            anchors.verticalCenter: parent.verticalCenter
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
