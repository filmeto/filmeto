// SkillWidget.qml - Widget for displaying skill/agent capability
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property string skillName: ""
    property string skillDescription: ""
    property var skillParams: ({})
    property color widgetColor: "#4a90e2"

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: skillColumn.height + 16

    Column {
        id: skillColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        // Skill name with icon
        Row {
            spacing: 8
            width: parent.width

            Text {
                text: "⚡"
                font.pixelSize: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                id: skillNameText
                text: root.skillName
                color: root.widgetColor
                font.pixelSize: 13
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Skill description
        Text {
            id: skillDescriptionText
            width: parent.width
            text: root.skillDescription
            color: "#888888"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            visible: root.skillDescription !== ""
        }

        // Skill parameters
        Rectangle {
            width: parent.width
            height: paramsColumn.implicitHeight + 12
            color: "#1a1a1a"
            radius: 4
            visible: Object.keys(root.skillParams || {}).length > 0

            Column {
                id: paramsColumn
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 8
                }
                spacing: 4

                Repeater {
                    model: Object.keys(root.skillParams || {}).length

                    Row {
                        spacing: 8
                        width: parent.width

                        Text {
                            text: Object.keys(root.skillParams)[index] + ":"
                            color: "#666666"
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: String(Object.values(root.skillParams)[index])
                            color: "#888888"
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }
        }
    }
}
