// SkillWidget.qml - Skill execution display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var skillData: ({})  // Maps to SkillContent.data: {skill_name, state, progress_text, progress_percentage, result, error_message}
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: skillColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: skillColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon and skill name
        Row {
            width: parent.width
            spacing: 8

            // Skill icon
            Rectangle {
                width: 24
                height: 24
                radius: 4
                color: root.widgetColor
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "⚡"
                    font.pixelSize: 14
                }
            }

            // Skill name
            Text {
                width: parent.width - 24 - parent.spacing
                text: root.skillData.skill_name || root.skillData.name || "Skill"
                color: "#e0e0e0"
                font.pixelSize: 13
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Status indicator
        Row {
            visible: (root.skillData.state || root.skillData.status) > ""
            width: parent.width
            spacing: 8

            // Status dot
            Rectangle {
                width: 8
                height: 8
                radius: width / 2
                color: getStatusColor(root.skillData.state || root.skillData.status)
                anchors.verticalCenter: parent.verticalCenter

                // Animation for in_progress
                SequentialAnimation on opacity {
                    running: (root.skillData.state || root.skillData.status) === "in_progress"
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.3; duration: 500 }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 500 }
                }
            }

            // Status text
            Text {
                text: formatSkillStatus(root.skillData.state || root.skillData.status || "")
                color: getStatusColor(root.skillData.state || root.skillData.status)
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Progress bar
        Rectangle {
            visible: (root.skillData.state || root.skillData.status) === "in_progress"
            width: parent.width
            height: 4
            color: "#404040"
            radius: 2

            Rectangle {
                width: parent.width * ((root.skillData.progress_percentage || root.skillData.progress || 0) / 100)
                height: parent.height
                color: root.widgetColor
                radius: parent.radius

                Behavior on width {
                    NumberAnimation { duration: 300 }
                }
            }
        }

        // Progress text
        Text {
            visible: (root.skillData.state || root.skillData.status) === "in_progress" && (root.skillData.progress_text || "") > ""
            width: parent.width
            text: root.skillData.progress_text || ""
            color: "#a0a0a0"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }

        // Result (shown when completed)
        Text {
            visible: (root.skillData.state || root.skillData.status) === "completed" && (root.skillData.result || "") > ""
            width: parent.width
            text: "✓ " + (root.skillData.result || "")
            color: "#4ecdc4"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Error (shown when failed)
        Text {
            visible: (root.skillData.state || root.skillData.status) === "error" && (root.skillData.error_message || root.skillData.error || "") > ""
            width: parent.width
            text: "✗ " + (root.skillData.error_message || root.skillData.error || "")
            color: "#ff6b6b"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    // Get status color
    function getStatusColor(status) {
        switch (status) {
            case "completed": return "#4ecdc4"
            case "error": return "#ff6b6b"
            case "in_progress": return root.widgetColor
            case "pending": return "#808080"
            default: return "#808080"
        }
    }

    // Format status text
    function formatSkillStatus(status) {
        switch (status) {
            case "completed": return "Completed"
            case "error": return "Failed"
            case "in_progress": return "Running..."
            case "pending": return "Pending"
            default: return status
        }
    }
}
