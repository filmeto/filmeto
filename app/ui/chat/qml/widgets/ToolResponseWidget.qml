// ToolResponseWidget.qml - Tool/function response display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string toolName: ""
    property string response: ""
    property bool isError: false

    readonly property color bgColor: isError ? "#2a1a1a" : "#1a2a1a"
    readonly property color borderColor: isError ? "#804040" : "#406040"
    readonly property color textColor: "#d0d0d0"
    readonly property color iconColor: isError ? "#ff6b6b" : "#51cf66"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    width: parent ? parent.width : 0
    height: column.implicitHeight + 16  // 2 * margins (8)
    implicitWidth: width
    implicitHeight: height

    Layout.fillWidth: true

    property bool expanded: false

    ColumnLayout {
        id: column
        anchors {
            fill: parent
            margins: 8
        }
        spacing: 8

        // Header row
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Status icon
            Text {
                text: isError ? "❌" : "✅"
                font.pixelSize: 14
            }

            // Tool name and status
            Text {
                text: root.toolName + (root.isError ? " <font color='#ff6b6b'>failed</font>" : " <font color='#51cf66'>completed</font>")
                color: textColor
                font.pixelSize: 13
                textFormat: Text.RichText
            }

            Item { Layout.fillWidth: true }

            // Expand/collapse indicator
            Text {
                text: root.expanded ? "▼" : "▶"
                color: textColor
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.expanded = !root.expanded
                }
            }
        }

        // Response content (collapsible)
        Loader {
            Layout.fillWidth: true
            active: root.expanded
            sourceComponent: ColumnLayout {
                spacing: 4

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: borderColor
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(responseText.implicitHeight + 8, 300)

                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Text {
                        id: responseText
                        width: parent.width
                        padding: 4
                        text: root.response
                        color: textColor
                        font.pixelSize: 12
                        font.family: "monospace"
                        wrapMode: Text.Wrap
                        textFormat: Text.PlainText
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                        contentItem: Rectangle {
                            implicitWidth: 8
                            radius: width / 2
                            color: parent.hovered ? "#606060" : "#505050"
                            opacity: parent.active ? 1.0 : 0.5
                        }
                    }
                }
            }
        }
    }

    // Click header to toggle
    MouseArea {
        anchors.fill: parent
        propagateComposedEvents: true
        onPressed: function(mouse) {
            if (mouse.y < 40) {
                root.expanded = !root.expanded
                mouse.accepted = true
            } else {
                mouse.accepted = false
            }
        }
    }
}
