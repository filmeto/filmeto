// PlanTaskWidget.qml - Lightweight widget for PlanTask status updates
//
// This widget displays a single task status change,
// without showing the entire plan structure.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    // Input data
    property var updateData: ({})

    // Styling
    property color widgetColor: "#4a90e2"
    property color textColor: "#e1e1e1"
    property color dimTextColor: "#9a9a9a"
    property color bgColor: "#252525"
    property color borderColor: "#3a3a3a"

    implicitHeight: contentColumn.height + 12
    color: "transparent"
    radius: 6

    // Status colors
    property color runningColor: "#f4c542"
    property color waitingColor: "#3498db"
    property color completedColor: "#2ecc71"
    property color failedColor: "#e74c3c"

    // Helper functions
    function getStatusColor(status) {
        switch (status) {
            case "running": return runningColor
            case "completed": return completedColor
            case "failed":
            case "cancelled": return failedColor
            default: return waitingColor
        }
    }

    function getStatusIcon(status) {
        switch (status) {
            case "running": return "R"
            case "completed": return "S"
            case "failed":
            case "cancelled": return "F"
            default: return "W"
        }
    }

    function getStatusEmoji(status) {
        switch (status) {
            case "running": return "⏳"
            case "completed": return "✅"
            case "failed":
            case "cancelled": return "❌"
            default: return "⏸️"
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 8

        // Task status row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Status icon
            Rectangle {
                width: 20
                height: 20
                radius: 10
                color: getStatusColor(updateData.task_status)

                Text {
                    anchors.centerIn: parent
                    text: getStatusIcon(updateData.task_status)
                    color: "white"
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            // Task info
            Column {
                Layout.fillWidth: true
                spacing: 4

                // Task name
                Text {
                    id: taskNameText
                    width: parent.width
                    text: updateData.task_name || "Task Updated"
                    color: textColor
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    wrapMode: Text.NoWrap
                }

                // Status transition
                Row {
                    spacing: 4

                    Text {
                        id: statusText
                        text: {
                            var prev = updateData.previous_status
                            var curr = updateData.task_status
                            if (prev && prev !== curr) {
                                return prev + " → " + curr
                            } else {
                                return curr || "unknown"
                            }
                        }
                        color: dimTextColor
                        font.pixelSize: 11
                    }

                    // Crew member (if available)
                    Row {
                        visible: updateData.crew_member !== undefined && updateData.crew_member !== null
                        spacing: 4

                        Rectangle {
                            width: 16
                            height: 16
                            radius: 3
                            color: (updateData.crew_member && updateData.crew_member.color) || "#5c5f66"

                            Text {
                                anchors.centerIn: parent
                                text: (updateData.crew_member && updateData.crew_member.icon) || "A"
                                color: "white"
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }

                        Text {
                            text: (updateData.crew_member && updateData.crew_member.name) || "Unknown"
                            color: dimTextColor
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }
}
