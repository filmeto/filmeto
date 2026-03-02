// TaskItemDelegate.qml - Reusable task item delegate for PlanWidget and PlanTaskWidget
//
// This component displays a single task with status, name, description,
// crew member info, dependencies, and error message.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    // === Input Properties ===
    property var taskData: ({})  // {id, name, status, description, title, crew_member, needs, error_message}
    property color widgetColor: "#4a90e2"

    // Display options
    property bool showStatusTransition: false  // Whether to show status transition (start -> end)
    property string previousStatus: ""  // Previous status for transition display
    property bool showCrewMember: true  // Whether to show crew member info

    // Styling
    property color bgColor: "#2b2d30"
    property color textColor: "#e1e1e1"
    property color dimTextColor: "#9a9a9a"

    // Status colors
    property color runningColor: "#f4c542"
    property color waitingColor: "#3498db"
    property color completedColor: "#2ecc71"
    property color failedColor: "#e74c3c"

    // Layout
    implicitHeight: contentColumn.height + 16
    implicitWidth: 200
    color: root.bgColor
    radius: 4

    // Computed properties
    readonly property string currentStatus: taskData.status || "waiting"
    readonly property bool hasTransition: showStatusTransition && previousStatus.length > 0 && previousStatus !== currentStatus

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

    function getStatusText(status) {
        switch (status) {
            case "running": return qsTr("Running")
            case "completed": return qsTr("Completed")
            case "failed": return qsTr("Failed")
            case "cancelled": return qsTr("Cancelled")
            case "waiting": return qsTr("Waiting")
            case "ready": return qsTr("Ready")
            case "created": return qsTr("Created")
            default: return status || qsTr("Unknown")
        }
    }

    // Task content column
    Column {
        id: contentColumn
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: 8
        }
        spacing: 6

        // Row 1: Status + Task name + Status display
        RowLayout {
            width: parent.width
            spacing: 6

            // Status icon (current status)
            Rectangle {
                width: 18
                height: 18
                radius: 9
                color: getStatusColor(currentStatus)

                // Running animation
                SequentialAnimation on opacity {
                    running: currentStatus === "running"
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.5; duration: 500 }
                    NumberAnimation { to: 1.0; duration: 500 }
                }

                Text {
                    anchors.centerIn: parent
                    text: getStatusIcon(currentStatus)
                    color: "white"
                    font.pixelSize: 10
                    font.bold: true
                }
            }

            // Task name
            Text {
                Layout.fillWidth: true
                text: taskData.name || taskData.task_name || qsTr("Untitled Task")
                color: textColor
                font.pixelSize: 13
                font.bold: true
                elide: Text.ElideRight
                maximumLineCount: 1
                wrapMode: Text.NoWrap
            }

            // Status display - different based on context
            Row {
                spacing: 4

                // Status transition display (for PlanTaskWidget)
                Row {
                    visible: hasTransition
                    spacing: 4

                    // Previous status badge
                    Rectangle {
                        width: prevStatusText.width + 8
                        height: 16
                        radius: 3
                        color: getStatusColor(previousStatus)
                        opacity: 0.6

                        Text {
                            id: prevStatusText
                            anchors.centerIn: parent
                            text: getStatusText(previousStatus)
                            color: "white"
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }

                    // Arrow
                    Text {
                        text: "→"
                        color: widgetColor
                        font.pixelSize: 12
                        font.bold: true
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    // Current status badge
                    Rectangle {
                        width: currStatusText.width + 8
                        height: 16
                        radius: 3
                        color: getStatusColor(currentStatus)

                        Text {
                            id: currStatusText
                            anchors.centerIn: parent
                            text: getStatusText(currentStatus)
                            color: "white"
                            font.pixelSize: 9
                            font.bold: true
                        }
                    }
                }

                // Single status display (for PlanWidget - terminal status only)
                Rectangle {
                    visible: !hasTransition
                    width: singleStatusText.width + 8
                    height: 16
                    radius: 3
                    color: getStatusColor(currentStatus)

                    Text {
                        id: singleStatusText
                        anchors.centerIn: parent
                        text: getStatusText(currentStatus)
                        color: "white"
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }
        }

        // Row 2: Task description (shown when available)
        Text {
            visible: taskData.description && taskData.description.length > 0
            width: parent.width
            text: taskData.description || ""
            color: dimTextColor
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            elide: Text.ElideRight
            leftPadding: 24
        }

        // Row 3: Crew member + Dependencies
        RowLayout {
            width: parent.width
            spacing: 6

            // Crew avatar + name
            Row {
                visible: showCrewMember
                spacing: 4

                Rectangle {
                    width: 20
                    height: 20
                    radius: 4
                    color: {
                        var cm = taskData.crew_member
                        return cm && cm.color ? cm.color : "#5c5f66"
                    }

                    Text {
                        anchors.centerIn: parent
                        text: {
                            var cm = taskData.crew_member
                            return cm && cm.icon ? cm.icon : "A"
                        }
                        color: "white"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                Text {
                    text: {
                        var cm = taskData.crew_member
                        if (cm && cm.name) return cm.name
                        return taskData.title || qsTr("Unknown")
                    }
                    color: dimTextColor
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // Separator
            Rectangle {
                visible: taskData.needs && taskData.needs.length > 0
                width: 1
                height: 14
                color: "#4a4a4a"
            }

            // Dependencies
            Row {
                visible: taskData.needs && taskData.needs.length > 0
                spacing: 4

                Text {
                    text: qsTr("Depends on:")
                    color: "#777"
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }

                Repeater {
                    model: taskData.needs || []

                    Rectangle {
                        width: depText.width + 8
                        height: 16
                        radius: 3
                        color: "#3a3a3a"

                        Text {
                            id: depText
                            anchors.centerIn: parent
                            text: modelData
                            color: "#aaa"
                            font.pixelSize: 9
                            font.family: "monospace"
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            // Task ID badge (if available)
            Rectangle {
                visible: taskData.id && taskData.id.length > 0
                width: taskIdText.width + 8
                height: 16
                radius: 3
                color: "#3a3a3a"

                Text {
                    id: taskIdText
                    anchors.centerIn: parent
                    text: taskData.id || ""
                    color: dimTextColor
                    font.pixelSize: 9
                    font.family: "monospace"
                }
            }
        }

        // Row 4: Error message (if task failed)
        Rectangle {
            visible: (taskData.status === "failed" || taskData.status === "cancelled") &&
                     taskData.error_message && taskData.error_message.length > 0
            width: parent.width
            height: errorText.height + 10
            radius: 3
            color: "#4a2020"

            Text {
                id: errorText
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    margins: 5
                }
                text: qsTr("Error:") + " " + (taskData.error_message || qsTr("Unknown error"))
                color: "#ff6b6b"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }
        }
    }
}
