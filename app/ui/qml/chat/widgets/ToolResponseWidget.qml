// ToolResponseWidget.qml - Tool/function response display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string toolName: ""
    property string response: ""
    property bool isError: false
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#e0e0e0"
    readonly property color iconColor: isError ? "#ff6b6b" : "#4ecdc4"

    color: bgColor
    radius: 6
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: responseColumn.implicitHeight + 24

    Layout.fillWidth: true

    property bool expanded: false

    Column {
        id: responseColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon and tool name - clickable for expand/collapse
        Item {
            width: parent.width
            height: headerRow.implicitHeight

            Row {
                id: headerRow
                width: parent.width
                spacing: 8

                // Status icon with colored background
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: root.iconColor
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: isError ? "✕" : "✓"
                        font.pixelSize: 14
                        color: "#ffffff"
                    }
                }

                // Tool name with selection support
                SelectableText {
                    width: parent.width - 24 - parent.spacing - expandIndicator.width - 30
                    text: root.toolName + (root.isError ? " failed" : " completed")
                    textColor: textColor
                    fontPixelSize: 13
                    wrapMode: true
                    selectionColor: root.widgetColor
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Expand/collapse indicator
                Text {
                    id: expandIndicator
                    text: root.expanded ? "▼" : "▶"
                    color: textColor
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // MouseArea only on header - child components can receive their own clicks
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
            }
        }

        // Expanded content
        Column {
            visible: root.expanded
            width: parent.width
            spacing: 8

            // Separator
            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            // Response content
            SelectableText {
                width: parent.width
                text: (root.isError ? "✗ " : "✓ ") + root.response
                textColor: root.iconColor
                fontPixelSize: 12
                wrapMode: true
                selectionColor: root.iconColor
            }
        }
    }
}
