// Panel.qml - Full-height panel container
// Use for sidebar panels and main content areas

import QtQuick 2.15
import ".."

Rectangle {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Content
    default property alias content: contentItem.data

    // Title (optional header)
    property string title: ""
    property bool showHeader: title !== ""

    // Toolbar actions
    property alias toolbar: toolbarLoader.sourceComponent

    // ─────────────────────────────────────────────────────────────
    // Rectangle Configuration
    // ─────────────────────────────────────────────────────────────
    color: Theme.background

    // ─────────────────────────────────────────────────────────────
    // Layout
    // ─────────────────────────────────────────────────────────────
    Column {
        id: column
        anchors.fill: parent

        // Header (if title is set)
        Item {
            id: headerItem
            visible: root.showHeader
            width: parent.width
            height: visible ? 40 : 0

            Row {
                anchors.fill: parent
                anchors.leftMargin: Theme.spacingMedium
                anchors.rightMargin: Theme.spacingSmall
                spacing: Theme.spacingSmall

                Text {
                    text: root.title
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontLarge
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter
                }

                Item { width: 1; Layout.fillWidth: true }

                Loader {
                    id: toolbarLoader
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // Bottom border
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.border
            }
        }

        // Content
        Item {
            id: contentItem
            width: parent.width
            height: parent.height - headerItem.height
        }
    }
}
