// StepWidget.qml - Widget for displaying step/task progress
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property string stepNumber: ""
    property string stepTitle: ""
    property string stepDescription: ""
    property string status: "pending"  // pending, active, completed, error
    property var widgetColor: "#4a90e2"

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: stepColumn.height + 16

    Column {
        id: stepColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        Row {
            spacing: 10
            width: parent.width

            // Step indicator
            Rectangle {
                id: stepIndicator
                width: 24
                height: 24
                radius: width / 2
                color: {
                    if (root.status === "completed") return "#4caf50"
                    if (root.status === "active") return root.widgetColor
                    if (root.status === "error") return "#f44336"
                    return "#555555"
                }
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: {
                        if (root.status === "completed") return "✓"
                        if (root.status === "error") return "✗"
                        return root.stepNumber || ""
                    }
                    color: "#ffffff"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                }
            }

            // Step title
            Text {
                id: stepTitleText
                text: root.stepTitle
                color: "#e0e0e0"
                font.pixelSize: 13
                font.weight: root.status === "active" ? Font.Medium : Font.Normal
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Step description
        Text {
            id: stepDescriptionText
            width: parent.width
            text: root.stepDescription
            color: "#888888"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            visible: root.stepDescription !== ""
        }
    }
}
