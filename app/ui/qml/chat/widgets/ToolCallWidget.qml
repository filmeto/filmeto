// ToolCallWidget.qml - Tool/function call display with result support
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string toolName: ""
    property var toolArgs: ({})
    property string toolStatus: "started"  // started, completed, failed
    property var result: null
    property string error: ""
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: {
        if (toolStatus === "failed") return "#2a1a1a"
        if (toolStatus === "completed") return "#1a2a1a"
        return "#2a2a2a"
    }
    readonly property color borderColor: {
        if (toolStatus === "failed") return "#804040"
        if (toolStatus === "completed") return "#406040"
        return Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    }
    readonly property color textColor: "#d0d0d0"
    readonly property color accentColor: widgetColor
    readonly property color statusColor: {
        if (toolStatus === "failed") return "#ff6b6b"
        if (toolStatus === "completed") return "#51cf66"
        return widgetColor
    }

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: column.implicitHeight + 12

    Layout.fillWidth: true

    property bool expanded: false

    // Status icon based on tool status
    readonly property string statusIcon: {
        if (toolStatus === "failed") return "❌"
        if (toolStatus === "completed") return "✅"
        return "🔧"
    }

    // Status text
    readonly property string statusText: {
        if (toolStatus === "failed") return "failed"
        if (toolStatus === "completed") return "completed"
        return "running"
    }

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

            // Status/Tool icon
            Text {
                text: root.statusIcon
                font.pixelSize: 14
            }

            // Tool name and status
            Text {
                text: {
                    if (root.toolStatus === "started")
                        return "Calling: <b>" + root.toolName + "</b>"
                    return root.toolName + " <font color='" + root.statusColor + "'>" + root.statusText + "</font>"
                }
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

        // Expanded content
        Loader {
            Layout.fillWidth: true
            Layout.preferredHeight: active ? implicitHeight : 0
            visible: active
            active: root.expanded
            sourceComponent: ColumnLayout {
                spacing: 4

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: borderColor
                }

                // Arguments display
                ColumnLayout {
                    spacing: 4
                    visible: Object.keys(root.toolArgs || {}).length > 0

                    Text {
                        text: "Arguments:"
                        color: accentColor
                        font.pixelSize: 12
                        font.bold: true
                    }

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

                // Result/Error display
                ColumnLayout {
                    spacing: 4
                    visible: root.result !== null || root.error !== ""

                    Text {
                        text: root.error ? "Error:" : "Result:"
                        color: root.error ? "#ff6b6b" : "#51cf66"
                        font.pixelSize: 12
                        font.bold: true
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(resultText.implicitHeight + 8, 300)
                        visible: root.result !== null || root.error !== ""

                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                        Text {
                            id: resultText
                            width: parent.width
                            padding: 4
                            text: root.error || JSON.stringify(root.result, null, 2)
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
