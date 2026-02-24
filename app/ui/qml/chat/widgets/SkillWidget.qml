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

    readonly property int childCount: (root.skillData.child_contents || []).length

    implicitWidth: parent.width
    implicitHeight: skillColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: skillColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon, skill name, and expand indicator
        // Click header to toggle expand/collapse
        Item {
            width: parent.width
            height: headerRow.implicitHeight

            Row {
                id: headerRow
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

            // MouseArea only on header - child components can receive their own clicks
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
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

        // Nested child contents (tool calls, etc.) - displayed flat when expanded
        Column {
            visible: root.expanded && root.childCount > 0
            width: parent.width
            spacing: 8

            // Separator
            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            // Child contents list - using full structured content widgets
            Repeater {
                model: root.skillData.child_contents || []

                delegate: Loader {
                    width: parent.width
                    sourceComponent: resolveChildComponent(modelData.content_type || modelData.data?.content_type || "text")

                    property var itemData: modelData
                }
            }
        }
    }

    // Resolve the correct widget component for a content type
    function resolveChildComponent(contentType) {
        switch (contentType) {
            case "tool_call":
                return toolCallWidgetComponent;
            case "tool_response":
                return toolResponseWidgetComponent;
            case "thinking":
                return thinkingWidgetComponent;
            case "step":
                return stepWidgetComponent;
            case "plan":
                return planWidgetComponent;
            case "task":
                return taskWidgetComponent;
            case "progress":
                return progressWidgetComponent;
            case "error":
                return errorWidgetComponent;
            case "llm_output":
                return llmOutputWidgetComponent;
            case "metadata":
                return metadataWidgetComponent;
            case "skill":
                return skillWidgetComponent;
            default:
                return textFallbackComponent;
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Widget Components (reuse existing structured content widgets)
    // ─────────────────────────────────────────────────────────────

    // Tool call widget
    Component {
        id: toolCallWidgetComponent
        ToolCallWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            toolName: itemData.data?.tool_name || itemData.tool_name || ""
            toolArgs: itemData.data?.tool_args || itemData.tool_args || {}
            toolStatus: itemData.data?.status || itemData.status || "started"
            result: itemData.data?.result !== undefined ? itemData.data.result : (itemData.result !== undefined ? itemData.result : null)
            error: itemData.data?.error || itemData.error || ""
        }
    }

    // Tool response widget
    Component {
        id: toolResponseWidgetComponent
        ToolResponseWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            toolName: itemData.data?.tool_name || itemData.tool_name || ""
            response: itemData.data?.response || itemData.response || ""
            isError: itemData.data?.is_error || itemData.is_error || false
        }
    }

    // Thinking widget
    Component {
        id: thinkingWidgetComponent
        ThinkingWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            thought: itemData.data?.thought || itemData.thought || ""
            title: itemData.title || itemData.data?.title || "Thinking Process"
            isCollapsible: true
        }
    }

    // Step widget
    Component {
        id: stepWidgetComponent
        StepWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            stepData: ({
                title: itemData.title || itemData.data?.title || "",
                description: itemData.description || itemData.data?.description || "",
                status: itemData.data?.status || itemData.status || "pending",
                step_number: itemData.data?.step_number || itemData.step_number || 0
            })
        }
    }

    // Plan widget
    Component {
        id: planWidgetComponent
        PlanWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            planData: itemData
        }
    }

    // Task widget
    Component {
        id: taskWidgetComponent
        TaskWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            taskData: itemData
        }
    }

    // Progress widget
    Component {
        id: progressWidgetComponent
        ProgressWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            text: itemData.data?.progress || itemData.progress || ""
            percentage: itemData.data?.percentage || itemData.percentage || null
        }
    }

    // Error widget
    Component {
        id: errorWidgetComponent
        ErrorWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            errorData: ({
                error_message: itemData.data?.error || itemData.error_message || "",
                error_type: itemData.data?.error_type || itemData.error_type || (itemData.title || "Error"),
                details: itemData.description || itemData.data?.description || ""
            })
        }
    }

    // LLM output widget
    Component {
        id: llmOutputWidgetComponent
        LlmOutputWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            output: itemData.data?.output || itemData.output || ""
            title: itemData.title || itemData.data?.title || "LLM Output"
        }
    }

    // Metadata widget
    Component {
        id: metadataWidgetComponent
        MetadataWidget {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.8)
            metadataData: ({
                metadata_type: itemData.data?.metadata_type || itemData.title || "",
                title: itemData.title || "",
                description: itemData.description || "",
                metadata_data: itemData.data?.data || itemData.data || {}
            })
        }
    }

    // Nested skill widget - use source property to avoid recursive instantiation
    Component {
        id: skillWidgetComponent
        Loader {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            source: "SkillWidget.qml"
            property var _skillData: itemData.data || itemData
            property color _widgetColor: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.7)

            onLoaded: {
                item.skillData = _skillData
                item.widgetColor = _widgetColor
            }
        }
    }

    // Fallback text display
    Component {
        id: textFallbackComponent
        Rectangle {
            // itemData is set by Loader via property var itemData: modelData
            width: parent.width
            height: fallbackText.implicitHeight + 12
            color: "#1a1a1a"
            radius: 4
            border.color: "#303030"
            border.width: 1

            Text {
                id: fallbackText
                anchors {
                    fill: parent
                    margins: 8
                }
                text: JSON.stringify(itemData)
                color: "#808080"
                font.pixelSize: 10
                wrapMode: Text.WordWrap
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
