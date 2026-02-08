// ErrorMessageBubble.qml - Error message display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string senderName: ""
    property string content: ""
    property color agentColor: "#ff6b6b"
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
                    text: "⚠️"
                    font.pixelSize: 18
                }
            }

            Text {
                text: root.senderName || "Error"
                color: root.agentColor
                font.pixelSize: 13
                font.weight: Font.Medium
            }
        }

        // Error content
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredWidth: Math.min(parent.width, 700)
            Layout.maximumWidth: 700

            color: "#2a1a1a"
            radius: 12
            border.color: "#804040"
            border.width: 1

            ColumnLayout {
                anchors {
                    fill: parent
                    margins: 12
                }
                spacing: 8

                // Error icon and text
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: "❌"
                        font.pixelSize: 16
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.content
                        color: "#ff6b6b"
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                    }
                }

                // Structured error details if available
                Repeater {
                    model: root.structuredContent

                    delegate: Loader {
                        Layout.fillWidth: true

                        sourceComponent: {
                            if (modelData.content_type === "error") {
                                return errorDetailComponent
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
        id: errorDetailComponent

        ColumnLayout {
            spacing: 4

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: "#504040"
            }

            Text {
                Layout.fillWidth: true
                text: itemData.error_message || itemData.data.error_message || ""
                color: "#d0d0d0"
                font.pixelSize: 12
                font.family: "monospace"
                wrapMode: Text.WordWrap
            }

            // Stack trace if available
            Text {
                visible: itemData.stack_trace || itemData.data.stack_trace
                Layout.fillWidth: true
                text: itemData.stack_trace || itemData.data.stack_trace || ""
                color: "#a0a0a0"
                font.pixelSize: 11
                font.family: "monospace"
                wrapMode: Text.WordWrap
            }
        }
    }
}
