// EmptyState.qml - Placeholder for empty content
// Use when lists or containers have no data

import QtQuick 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    property string message: ""
    property string icon: ""  // Emoji or icon character
    property string description: ""

    // Action button (optional)
    property string actionText: ""
    signal actionTriggered()

    // ─────────────────────────────────────────────────────────────
    // Layout Configuration
    // ─────────────────────────────────────────────────────────────
    spacing: Theme.spacingMedium

    // ─────────────────────────────────────────────────────────────
    // Content
    // ─────────────────────────────────────────────────────────────

    // Icon
    Text {
        visible: root.icon !== ""
        text: root.icon
        font.pixelSize: 48
        Layout.alignment: Qt.AlignHCenter
    }

    // Message
    Text {
        text: root.message
        color: Theme.textSecondary
        font.pixelSize: Theme.fontDefault
        font.bold: true
        Layout.alignment: Qt.AlignHCenter
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
    }

    // Description
    Text {
        visible: root.description !== ""
        text: root.description
        color: Theme.textTertiary
        font.pixelSize: Theme.fontSmall
        Layout.alignment: Qt.AlignHCenter
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
        horizontalAlignment: Text.AlignHCenter
        Layout.maximumWidth: 300
    }

    // Action button
    Loader {
        visible: root.actionText !== ""
        Layout.alignment: Qt.AlignHCenter
        sourceComponent: root.actionText !== "" ? actionButtonComponent : null
    }

    Component {
        id: actionButtonComponent
        Button {
            text: root.actionText
            onClicked: root.actionTriggered()

            background: Rectangle {
                radius: Theme.radiusMedium
                color: parent.hovered ? Theme.accentHover : Theme.accent
            }

            contentItem: Text {
                text: parent.text
                color: "white"
                font.pixelSize: Theme.fontMedium
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
