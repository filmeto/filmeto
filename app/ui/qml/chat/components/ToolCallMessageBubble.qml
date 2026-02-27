// ToolCallMessageBubble.qml - Message showing tool calls
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

        // Tool calls
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
                            if (modelData.content_type === "tool_call") {
                                return toolCallComponent
                            } else if (modelData.content_type === "tool_response") {
                                return toolResponseComponent
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
        id: toolCallComponent

        ToolCallWidget {
            widgetColor: root.agentColor
            toolName: itemData.data?.tool_name || itemData.tool_name || ""
            toolArgs: itemData.data?.tool_input || itemData.tool_input || {}
            toolStatus: itemData.data?.status || itemData.status || "started"
            result: itemData.data?.result !== undefined ? itemData.data.result : (itemData.result !== undefined ? itemData.result : null)
            error: itemData.data?.error || itemData.error || ""
        }
    }

    Component {
        id: toolResponseComponent

        ToolResponseWidget {
            toolName: itemData.tool_name || itemData.data?.tool_name || ""
            response: itemData.response || itemData.data?.response || ""
            isError: itemData.is_error || itemData.data?.is_error || false
        }
    }
}
