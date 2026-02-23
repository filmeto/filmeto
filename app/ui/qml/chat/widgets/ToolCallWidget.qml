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

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#e0e0e0"
    readonly property color accentColor: widgetColor

    // Tool icon based on tool name patterns
    readonly property string toolIcon: {
        var name = root.toolName.toLowerCase();
        if (name.includes("search") || name.includes("fetch")) return "🔍";
        if (name.includes("write") || name.includes("save") || name.includes("create")) return "📝";
        if (name.includes("read") || name.includes("load") || name.includes("get")) return "📖";
        if (name.includes("code") || name.includes("execute") || name.includes("run")) return "⚙️";
        if (name.includes("plan")) return "📋";
        if (name.includes("todo") || name.includes("task")) return "✅";
        if (name.includes("media") || name.includes("video") || name.includes("audio")) return "🎬";
        if (name.includes("image") || name.includes("picture")) return "🖼️";
        return "🔧";
    }

    // Status text
    readonly property string statusText: {
        if (toolStatus === "failed") return "Failed";
        if (toolStatus === "completed") return "Completed";
        return "Running..."
    }

    // Status color
    readonly property color statusColor: {
        if (toolStatus === "failed") return "#ff6b6b";
        if (toolStatus === "completed") return "#4ecdc4";
        return widgetColor;
    }

    color: bgColor
    radius: 6
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: toolColumn.implicitHeight + 24

    Layout.fillWidth: true

    property bool expanded: false

    Column {
        id: toolColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon and tool name - clickable for expand/collapse
        Item {
            width: parent.width
            height: headerRow.implicitHeight

            Row {
                id: headerRow
                width: parent.width
                spacing: 8

                // Tool icon with colored background
                Rectangle {
                    width: 24
                    height: 24
                    radius: 4
                    color: root.widgetColor
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: root.toolIcon
                        font.pixelSize: 14
                    }
                }

                // Tool name
                Text {
                    width: parent.width - 24 - parent.spacing - expandIndicator.width
                    text: root.toolName || "Tool"
                    color: textColor
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Expand/collapse indicator
                Text {
                    id: expandIndicator
                    text: root.expanded ? "▼" : "▶"
                    color: textColor
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            // MouseArea only on header - child components can receive their own clicks
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
            }
        }

        // Status indicator
        Row {
            visible: root.toolStatus > ""
            width: parent.width
            spacing: 8

            // Status dot
            Rectangle {
                width: 8
                height: 8
                radius: width / 2
                color: root.statusColor
                anchors.verticalCenter: parent.verticalCenter

                // Animation for running state
                SequentialAnimation on opacity {
                    running: root.toolStatus === "started"
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.3; duration: 500 }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 500 }
                }
            }

            // Status text
            Text {
                text: root.statusText
                color: root.statusColor
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Expanded content (arguments and result)
        Column {
            visible: root.expanded
            width: parent.width
            spacing: 8

            // Separator
            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            // Arguments display
            Column {
                visible: Object.keys(root.toolArgs || {}).length > 0
                width: parent.width
                spacing: 4

                Text {
                    text: "Arguments:"
                    color: "#a0a0a0"
                    font.pixelSize: 11
                }

                Repeater {
                    model: Object.keys(root.toolArgs || {})

                    delegate: Row {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: modelData + ":"
                            color: root.accentColor
                            font.pixelSize: 11
                            font.family: "monospace"
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            width: parent.width - modelData.width - parent.spacing
                            text: JSON.stringify(root.toolArgs[modelData])
                            color: "#d0d0d0"
                            font.pixelSize: 11
                            font.family: "monospace"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            // Result display (when completed)
            Text {
                visible: root.toolStatus === "completed" && root.result !== null
                width: parent.width
                text: "✓ " + (typeof root.result === "string" ? root.result : JSON.stringify(root.result))
                color: "#4ecdc4"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            // Error display (when failed)
            Text {
                visible: root.toolStatus === "failed" && root.error !== ""
                width: parent.width
                text: "✗ " + root.error
                color: "#ff6b6b"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }
    }
}
