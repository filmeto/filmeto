// StepWidget.qml - Step/progress indicator widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var stepData: ({})  // {title, description, status, step_number, total_steps}
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: stepColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: {
        if (root.stepData.status === "completed") return "#4ecdc4"
        if (root.stepData.status === "error") return "#ff6b6b"
        if (root.stepData.status === "in_progress") return root.widgetColor
        return "#404040"
    }
    border.width: 2

    Column {
        id: stepColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with step number and status
        Row {
            width: parent.width
            spacing: 8

            // Step number circle
            Rectangle {
                width: 28
                height: 28
                radius: width / 2
                color: getStepColor()
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: (root.stepData.step_number || 0).toString()
                    color: "#ffffff"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
            }

            // Title and status column
            Column {
                width: parent.width - 28 - parent.spacing
                spacing: 2

                // Title
                Text {
                    width: parent.width
                    text: root.stepData.title || "Step"
                    color: "#e0e0e0"
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                }

                // Status badge
                Rectangle {
                    visible: root.stepData.status > ""
                    width: statusText.implicitWidth + 12
                    height: 18
                    color: getStepColor()
                    radius: 3

                    Text {
                        id: statusText
                        anchors.centerIn: parent
                        text: formatStatus(root.stepData.status || "")
                        color: "#ffffff"
                        font.pixelSize: 9
                        font.weight: Font.Bold
                    }
                }
            }
        }

        // Description
        Text {
            visible: root.stepData.description > ""
            width: parent.width
            text: root.stepData.description || ""
            color: "#a0a0a0"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Progress bar (for in_progress status)
        Rectangle {
            visible: root.stepData.status === "in_progress"
            width: parent.width
            height: 4
            color: "#404040"
            radius: 2

            Rectangle {
                width: parent.width * ((root.stepData.progress || 0) / 100)
                height: parent.height
                color: getStepColor()
                radius: parent.radius

                Behavior on width {
                    NumberAnimation { duration: 300 }
                }
            }
        }

        // Additional info (e.g., duration)
        Text {
            visible: root.stepData.duration > ""
            width: parent.width
            text: "⏱ " + root.stepData.duration
            color: "#808080"
            font.pixelSize: 11
        }
    }

    // Get step color based on status
    function getStepColor() {
        var status = root.stepData.status || "pending"
        switch (status) {
            case "completed": return "#4ecdc4"
            case "error": return "#ff6b6b"
            case "in_progress": return root.widgetColor
            case "pending": return "#606060"
            default: return "#606060"
        }
    }

    // Format status text
    function formatStatus(status) {
        switch (status) {
            case "completed": return "DONE"
            case "error": return "FAILED"
            case "in_progress": return "IN PROGRESS"
            case "pending": return "PENDING"
            default: return status.toUpperCase()
        }
    }
}
