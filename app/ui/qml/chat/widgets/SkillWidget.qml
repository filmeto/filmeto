// SkillWidget.qml - Skill execution display widget with nested child contents
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var skillData: ({})  // Maps to SkillContent.data: {skill_name, state, progress_text, progress_percentage, result, error_message, child_contents, run_id}
    property color widgetColor: "#4a90e2"

    // Internal state for expand/collapse
    property bool expanded: false
    property bool childrenExpanded: false

    readonly property int childCount: (root.skillData.child_contents || []).length

    implicitWidth: parent.width
    implicitHeight: skillColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    // Click to toggle expand
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.expanded = !root.expanded
    }

    Column {
        id: skillColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon, skill name, and expand indicator
        Row {
            width: parent.width
            spacing: 8

            // Skill icon
            Rectangle {
                width: 24
                height: 24
                radius: 4
                color: root.widgetColor
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "⚡"
                    font.pixelSize: 14
                }
            }

            // Skill name
            Text {
                width: parent.width - 24 - expandIndicator.width - parent.spacing * 2
                text: root.skillData.skill_name || root.skillData.name || "Skill"
                color: "#e0e0e0"
                font.pixelSize: 13
                font.weight: Font.Medium
                wrapMode: Text.WordWrap
                anchors.verticalCenter: parent.verticalCenter
            }

            // Expand/collapse indicator
            Text {
                id: expandIndicator
                text: root.expanded ? "▼" : "▶"
                color: "#a0a0a0"
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Status indicator
        Row {
            visible: (root.skillData.state || root.skillData.status) > ""
            width: parent.width
            spacing: 8

            // Status dot
            Rectangle {
                width: 8
                height: 8
                radius: width / 2
                color: getStatusColor(root.skillData.state || root.skillData.status)
                anchors.verticalCenter: parent.verticalCenter

                // Animation for in_progress
                SequentialAnimation on opacity {
                    running: (root.skillData.state || root.skillData.status) === "in_progress"
                    loops: Animation.Infinite
                    NumberAnimation { from: 1.0; to: 0.3; duration: 500 }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 500 }
                }
            }

            // Status text
            Text {
                text: formatSkillStatus(root.skillData.state || root.skillData.status || "")
                color: getStatusColor(root.skillData.state || root.skillData.status)
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }

            // Child count indicator
            Text {
                visible: root.childCount > 0
                text: "• " + root.childCount + " step(s)"
                color: "#808080"
                font.pixelSize: 10
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Progress bar
        Rectangle {
            visible: (root.skillData.state || root.skillData.status) === "in_progress"
            width: parent.width
            height: 4
            color: "#404040"
            radius: 2

            Rectangle {
                width: parent.width * ((root.skillData.progress_percentage || root.skillData.progress || 0) / 100)
                height: parent.height
                color: root.widgetColor
                radius: parent.radius

                Behavior on width {
                    NumberAnimation { duration: 300 }
                }
            }
        }

        // Progress text
        Text {
            visible: root.expanded && (root.skillData.state || root.skillData.status) === "in_progress" && (root.skillData.progress_text || "") > ""
            width: parent.width
            text: root.skillData.progress_text || ""
            color: "#a0a0a0"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }

        // Result (shown when completed and expanded)
        Text {
            visible: root.expanded && (root.skillData.state || root.skillData.status) === "completed" && (root.skillData.result || "") > ""
            width: parent.width
            text: "✓ " + (root.skillData.result || "")
            color: "#4ecdc4"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Error (shown when failed and expanded)
        Text {
            visible: root.expanded && (root.skillData.state || root.skillData.status) === "error" && (root.skillData.error_message || root.skillData.error || "") > ""
            width: parent.width
            text: "✗ " + (root.skillData.error_message || root.skillData.error || "")
            color: "#ff6b6b"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Nested child contents (tool calls, etc.)
        Column {
            visible: root.expanded && root.childCount > 0
            width: parent.width
            spacing: 6

            // Separator
            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            // Child contents header with expand/collapse
            Row {
                width: parent.width
                spacing: 8

                Text {
                    text: "Execution Steps"
                    color: "#a0a0a0"
                    font.pixelSize: 11
                    font.bold: true
                }

                Item { width: 1; height: 1 }

                Text {
                    text: root.childrenExpanded ? "▼" : "▶"
                    color: "#808080"
                    font.pixelSize: 10

                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -8
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.childrenExpanded = !root.childrenExpanded
                    }
                }
            }

            // Child contents list
            Column {
                visible: root.childrenExpanded
                width: parent.width
                spacing: 4

                Repeater {
                    model: root.skillData.child_contents || []

                    delegate: Loader {
                        width: parent.width
                        sourceComponent: {
                            var contentType = modelData.content_type || modelData.data?.content_type;
                            switch (contentType) {
                                case "tool_call": return toolCallComponent;
                                case "tool_response": return toolResponseComponent;
                                default: return textFallbackComponent;
                            }
                        }

                        property var itemData: modelData

                        // Minimal tool call display for nested content
                        Component {
                            id: toolCallComponent
                            Rectangle {
                                width: parent.width
                                height: toolCallColumn.implicitHeight + 8
                                color: "#1a1a1a"
                                radius: 4
                                border.color: "#303030"
                                border.width: 1

                                Column {
                                    id: toolCallColumn
                                    anchors {
                                        fill: parent
                                        margins: 8
                                    }
                                    spacing: 4

                                    Row {
                                        width: parent.width
                                        spacing: 6

                                        Text {
                                            text: getToolIcon(itemData.data?.tool_name || "")
                                            font.pixelSize: 12
                                        }

                                        Text {
                                            text: itemData.data?.tool_name || "Tool"
                                            color: "#d0d0d0"
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                        }

                                        Item { width: 1; height: 1 }

                                        Text {
                                            text: getToolStatusText(itemData.data?.status || "started")
                                            color: getToolStatusColor(itemData.data?.status || "started")
                                            font.pixelSize: 10
                                        }
                                    }

                                    Text {
                                        visible: (itemData.data?.status === "completed") && (itemData.data?.result || "")
                                        width: parent.width
                                        text: "✓ " + (typeof itemData.data.result === "string" ? itemData.data.result : JSON.stringify(itemData.data.result))
                                        color: "#4ecdc4"
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        visible: (itemData.data?.status === "failed") && (itemData.data?.error || "")
                                        width: parent.width
                                        text: "✗ " + (itemData.data.error || "")
                                        color: "#ff6b6b"
                                        font.pixelSize: 11
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                function getToolIcon(name) {
                                    name = (name || "").toLowerCase();
                                    if (name.includes("search")) return "🔍";
                                    if (name.includes("write")) return "📝";
                                    if (name.includes("read")) return "📖";
                                    if (name.includes("code")) return "⚙️";
                                    if (name.includes("plan")) return "📋";
                                    return "🔧";
                                }

                                function getToolStatusText(status) {
                                    switch (status) {
                                        case "completed": return "Done";
                                        case "failed": return "Failed";
                                        default: return "Running...";
                                    }
                                }

                                function getToolStatusColor(status) {
                                    switch (status) {
                                        case "completed": return "#4ecdc4";
                                        case "failed": return "#ff6b6b";
                                        default: return root.widgetColor;
                                    }
                                }
                            }
                        }

                        // Minimal tool response display
                        Component {
                            id: toolResponseComponent
                            Rectangle {
                                width: parent.width
                                height: responseColumn.implicitHeight + 8
                                color: "#1a1a1a"
                                radius: 4
                                border.color: "#303030"
                                border.width: 1

                                Column {
                                    id: responseColumn
                                    anchors {
                                        fill: parent
                                        margins: 8
                                    }
                                    spacing: 4

                                    Text {
                                        text: (itemData.data?.is_error ? "✗ " : "✓ ") + (itemData.data?.tool_name || "Tool")
                                        color: itemData.data?.is_error ? "#ff6b6b" : "#4ecdc4"
                                        font.pixelSize: 11
                                    }
                                }
                            }
                        }

                        // Fallback text display
                        Component {
                            id: textFallbackComponent
                            Text {
                                width: parent.width
                                text: JSON.stringify(modelData)
                                color: "#808080"
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    // Get status color
    function getStatusColor(status) {
        switch (status) {
            case "completed": return "#4ecdc4"
            case "error": return "#ff6b6b"
            case "in_progress": return root.widgetColor
            case "pending": return "#808080"
            default: return "#808080"
        }
    }

    // Format status text
    function formatSkillStatus(status) {
        switch (status) {
            case "completed": return "Completed"
            case "error": return "Failed"
            case "in_progress": return "Running..."
            case "pending": return "Pending"
            default: return status
        }
    }
}
