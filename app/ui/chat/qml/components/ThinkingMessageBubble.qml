// ThinkingMessageBubble.qml - Message with thinking process
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string senderName: ""
    property color agentColor: "#4a90e2"
    property string agentIcon: "🤖"
    property var structuredContent: []

    signal referenceClicked(string refType, string refId)

    implicitWidth: parent.width
    implicitHeight: mainColumn.implicitHeight

    ColumnLayout {
        id: mainColumn
        anchors {
            left: parent.left
            right: parent.right
        }
        spacing: 4

        // Header
        RowLayout {
            spacing: 8

            Rectangle {
                width: 32
                height: 32
                radius: width / 2
                color: root.agentColor

                Text {
                    anchors.centerIn: parent
                    text: root.agentIcon
                    font.pixelSize: 18
                }
            }

            Text {
                text: root.senderName
                color: root.agentColor
                font.pixelSize: 13
                font.weight: Font.Medium
            }
        }

        // Thinking content
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredWidth: Math.min(parent.width, 700)
            Layout.maximumWidth: 700

            color: "#252525"
            radius: 12

            ThinkingWidget {
                anchors {
                    fill: parent
                    margins: 8
                }
                widgetColor: root.agentColor

                // Find thinking content from structured content
                thought: {
                    for (var i = 0; i < root.structuredContent.length; i++) {
                        if (root.structuredContent[i].content_type === "thinking") {
                            return root.structuredContent[i].thought || root.structuredContent[i].data.thought || ""
                        }
                    }
                    return ""
                }
                title: {
                    for (var i = 0; i < root.structuredContent.length; i++) {
                        if (root.structuredContent[i].content_type === "thinking") {
                            return root.structuredContent[i].title || root.structuredContent[i].data.title || "Thinking Process"
                        }
                    }
                    return "Thinking Process"
                }
                isCollapsible: true
            }
        }
    }
}
