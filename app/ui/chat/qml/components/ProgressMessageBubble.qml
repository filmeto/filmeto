// ProgressMessageBubble.qml - Message with progress indicators
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

        // Progress content
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredWidth: Math.min(parent.width, 700)
            Layout.maximumWidth: 700

            color: "#252525"
            radius: 12

            ColumnLayout {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 8

                Repeater {
                    model: root.structuredContent

                    delegate: Loader {
                        Layout.fillWidth: true

                        sourceComponent: {
                            if (modelData.content_type === "progress") {
                                return progressComponent
                            }
                            return null
                        }

                        property var itemData: modelData
                    }
                }
            }
        }
    }

    Component {
        id: progressComponent

        ProgressWidget {
            widgetColor: root.agentColor
            text: itemData.progress || itemData.data.progress || ""
            percentage: itemData.percentage || itemData.data.percentage || null
        }
    }
}
