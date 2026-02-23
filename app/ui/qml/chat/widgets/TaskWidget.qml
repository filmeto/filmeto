// TaskWidget.qml - Display task information
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var taskData: ({})  // Expected: {title, description, status, priority}
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#d0d0d0"
    readonly property color descColor: "#a0a0a0"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: taskColumn.implicitHeight + 16

    Layout.fillWidth: true

    property bool expanded: false

    ColumnLayout {
        id: taskColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row - clickable for expand/collapse
        Item {
            Layout.fillWidth: true
            height: headerRow.implicitHeight

            RowLayout {
                id: headerRow
                width: parent.width
                spacing: 8

                // Task icon
                Text {
                    text: "📌"
                    font.pixelSize: 14
                }

                // Title
                Text {
                    Layout.fillWidth: true
                    text: root.taskData.title || "Task"
                    color: textColor
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                }

                // Status badge
                Rectangle {
                    visible: root.taskData.status
                    Layout.preferredWidth: statusText.implicitWidth + 10
                    Layout.preferredHeight: 20
                    color: getStatusColor(root.taskData.status)
                    radius: 4

                    Text {
                        id: statusText
                        anchors.centerIn: parent
                        text: (root.taskData.status || "").toUpperCase()
                        color: "#ffffff"
                        font.pixelSize: 9
                        font.weight: Font.Medium
                    }
                }

                // Expand toggle
                Text {
                    visible: root.taskData.description
                    text: root.expanded ? "▼" : "▶"
                    color: descColor
                    font.pixelSize: 10
                }
            }

            // MouseArea only on header - child components can receive their own clicks
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.taskData.description) {
                        root.expanded = !root.expanded
                    }
                }
            }
        }

        // Description (collapsible)
        Loader {
            Layout.fillWidth: true
            Layout.preferredHeight: active ? implicitHeight : 0
            visible: active
            active: root.expanded && root.taskData.description
            sourceComponent: ColumnLayout {
                spacing: 6

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: borderColor
                }

                Text {
                    Layout.fillWidth: true
                    text: root.taskData.description || ""
                    color: descColor
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    lineHeight: 1.4
                }

                // Priority if available
                Text {
                    visible: root.taskData.priority
                    text: "Priority: " + root.taskData.priority
                    color: descColor
                    font.pixelSize: 11
                    font.italic: true
                }
            }
        }
    }

    function getStatusColor(status) {
        switch ((status || "").toLowerCase()) {
            case "done":
            case "completed":
            case "success": return "#51cf66"
            case "in_progress":
            case "running": return "#4a90e2"
            case "failed":
            case "error": return "#ff6b6b"
            case "pending":
            case "todo": return "#ffd43b"
            default: return "#808080"
        }
    }
}
