// ToolCallWidget.qml - Tool/function call display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string toolName: ""
    property var toolArgs: ({})
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#d0d0d0"
    readonly property color accentColor: widgetColor

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

            // Tool icon
            Text {
                text: "🔧"
                font.pixelSize: 14
            }

            // Tool name
            Text {
                text: "Calling: <b>" + root.toolName + "</b>"
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

        // Tool arguments (collapsible)
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

                // Arguments display
                Repeater {
                    model: Object.keys(root.toolArgs || {})

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Text {
                            text: modelData + ":"
                            color: accentColor
                            font.pixelSize: 12
                            font.family: "monospace"
                        }

                        Text {
                            Layout.fillWidth: true
                            text: JSON.stringify(root.toolArgs[modelData])
                            color: textColor
                            font.pixelSize: 12
                            font.family: "monospace"
                            wrapMode: Text.Wrap
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
