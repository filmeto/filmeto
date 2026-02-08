// AgentMessageBubble.qml - Left-aligned agent message with avatar and metadata
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

Item {
    id: root

    property string senderName: ""
    property color agentColor: "#4a90e2"
    property string agentIcon: "🤖"
    property var crewMetadata: ({})
    property var structuredContent: []  // Required: structured content array
    property string timestamp: ""

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color backgroundColor: "#353535"
    readonly property color textColor: "#e0e0e0"
    readonly property color nameColor: agentColor
    readonly property color timestampColor: "#888888"

    // Avatar dimensions
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Helper function to safely extract data values
    function safeGet(data, prop, defaultValue) {
        if (!data) return defaultValue
        if (data[prop] !== undefined) return data[prop]
        if (data.data && data.data[prop] !== undefined) return data.data[prop]
        return defaultValue
    }

    // Helper function to safely get nested data object
    function safeGetData(data, defaultObj) {
        if (!data) return defaultObj
        if (data.data !== undefined) return data.data
        return defaultObj
    }

    // Explicit width from parent (Loader) so layout is valid before anchors resolve
    width: parent ? parent.width : 0

    // Available width for content (minus left avatar space only); never negative
    readonly property int availableWidth: Math.max(0, (parent ? parent.width : 0) - (avatarSize + avatarSpacing))

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: headerRow.height + bubbleContainer.height + 20

    // Header row with avatar and name
    Row {
        id: headerRow
        anchors {
            left: parent.left
            leftMargin: 12
            top: parent.top
            topMargin: 12
        }
        spacing: 8
        height: Math.max(avatarRect.height, Math.max(nameColumn.implicitHeight, timestampText.implicitHeight))

        // Avatar/icon
        Rectangle {
            id: avatarRect
            width: 32
            height: 32
            radius: width / 2
            color: root.agentColor
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.agentIcon
                font.pixelSize: 18
            }
        }

        // Agent name and title column
        Column {
            id: nameColumn
            spacing: 4
            anchors.verticalCenter: parent.verticalCenter

            Row {
                spacing: 8
                height: nameText.implicitHeight

                Text {
                    id: nameText
                    text: root.senderName
                    color: nameColor
                    font.pixelSize: 13
                    font.weight: Font.Medium
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Timestamp (on the right of agent name)
                Text {
                    id: timestampText
                    text: root.timestamp
                    color: timestampColor
                    font.pixelSize: 11
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.timestamp !== ""
                }
            }

            // Crew title color block if available
            Rectangle {
                id: crewTitleBlock
                visible: root.crewMetadata !== undefined && root.crewMetadata.crew_title_display !== undefined && root.crewMetadata.crew_title_display !== ""
                width: crewTitleText.implicitWidth + 16
                height: 18
                color: root.agentColor
                radius: 3

                Text {
                    id: crewTitleText
                    anchors.centerIn: parent
                    text: (root.crewMetadata && root.crewMetadata.crew_title_display) || ""
                    color: "#ffffff"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                }
            }
        }
    }

    // Message content bubble - controls width and contains content
    Rectangle {
        id: bubbleContainer
        anchors {
            left: parent.left
            leftMargin: 40  // avatar (32) + spacing (8)
            top: headerRow.bottom
            topMargin: 12
        }
        // Maximum width for the bubble to prevent overflow; ensure non-negative
        width: Math.max(0, Math.min(availableWidth, 800))
        // Height is determined by content column
        height: contentColumn.height + 24

        // Bubble appearance
        color: backgroundColor
        radius: 12
        clip: true

        // Content column - properly constrained inside bubble
        Column {
            id: contentColumn
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 12
            }
            spacing: 8
            width: Math.max(0, parent.width - 24)

            // Render structured content
            Repeater {
                model: root.structuredContent || []

                delegate: Loader {
                    id: widgetLoader
                    // Constrain width to parent column width so content does not overflow
                    width: Math.max(0, contentColumn.width)

                    sourceComponent: {
                        var raw = modelData.content_type !== undefined ? modelData.content_type : (modelData.type !== undefined ? modelData.type : "text")
                        var type = String(raw).toLowerCase()
                        switch (type) {
                            // Basic content
                            case "text": return textWidgetComponent
                            case "code_block": return codeBlockComponent
                            // Thinking content
                            case "thinking": return thinkingWidgetComponent
                            // Tool content
                            case "tool_call": return toolCallComponent
                            case "tool_response": return toolResponseComponent
                            // Status content
                            case "typing": return typingIndicatorComponent
                            case "progress": return progressWidgetComponent
                            case "error": return errorWidgetComponent
                            // Media content
                            case "image": return imageWidgetComponent
                            case "video": return videoWidgetComponent
                            case "audio": return audioWidgetComponent
                            // Data content
                            case "table": return tableWidgetComponent
                            case "chart": return chartWidgetComponent
                            // Interactive content
                            case "link": return linkWidgetComponent
                            case "button": return buttonWidgetComponent
                            case "form": return formWidgetComponent
                            // Task and plan content
                            case "plan": return planWidgetComponent
                            case "task": return taskWidgetComponent
                            case "step": return stepWidgetComponent
                            case "task_list": return taskListWidgetComponent
                            case "skill": return skillWidgetComponent
                            // File content
                            case "file_attachment": return fileWidgetComponent
                            case "file": return fileWidgetComponent
                            // Metadata content
                            case "metadata": return metadataWidgetComponent
                            // Default fallback
                            default: return textWidgetComponent
                        }
                    }

                    property var widgetData: modelData
                    visible: {
                        var raw = modelData.content_type !== undefined ? modelData.content_type : (modelData.type !== undefined ? modelData.type : "text")
                        return String(raw).toLowerCase() !== "typing"
                    }

                    onLoaded: {
                        // Pass data to the widget
                        if (item.hasOwnProperty('data')) {
                            item.data = modelData
                        }
                        if (item.hasOwnProperty('widgetColor')) {
                            item.widgetColor = root.agentColor
                        }
                    }
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Widget Components
    // ─────────────────────────────────────────────────────────────

    // Text widget - width bound to parent (Loader) so text wraps inside bubble
    Component {
        id: textWidgetComponent

        Text {
            property var data: ({})
            text: root.safeGet(data, "text", root.safeGet(data, "content", ""))
            color: textColor
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            lineHeight: 1.5
            width: parent ? parent.width : 0
        }
    }

    // Code block widget
    Component {
        id: codeBlockComponent

        CodeBlockWidget {
            property var data: ({})
            width: parent.width
            code: root.safeGet(data, "code", "")
            language: root.safeGet(data, "language", "text")
        }
    }

    // Thinking widget (collapsible)
    Component {
        id: thinkingWidgetComponent

        ThinkingWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            thought: root.safeGet(data, "thought", "")
            title: root.safeGet(data, "title", "Thinking Process")
            isCollapsible: true
        }
    }

    // Tool call widget
    Component {
        id: toolCallComponent

        ToolCallWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            toolName: root.safeGet(data, "tool_name", "")
            toolArgs: root.safeGet(data, "tool_args", {})
        }
    }

    // Tool response widget
    Component {
        id: toolResponseComponent

        ToolResponseWidget {
            property var data: ({})
            width: parent.width
            toolName: root.safeGet(data, "tool_name", "")
            response: root.safeGet(data, "response", "")
            isError: root.safeGet(data, "is_error", false)
        }
    }

    // Typing indicator widget
    Component {
        id: typingIndicatorComponent

        Item {
            width: parent.width
            height: typingIndicator.height

            TypingIndicator {
                id: typingIndicator
                anchors.centerIn: parent
                active: true
            }
        }
    }

    // Progress widget
    Component {
        id: progressWidgetComponent

        ProgressWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            text: root.safeGet(data, "progress", "")
            percentage: root.safeGet(data, "percentage", null)
        }
    }

    // Image widget
    Component {
        id: imageWidgetComponent

        ImageWidget {
            property var data: ({})
            width: parent.width
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // Table widget
    Component {
        id: tableWidgetComponent

        TableWidget {
            property var data: ({})
            width: parent.width
            tableData: root.safeGetData(data, {})
        }
    }

    // Link widget
    Component {
        id: linkWidgetComponent

        LinkWidget {
            property var data: ({})
            width: parent.width
            url: root.safeGet(data, "url", "")
            title: root.safeGet(data, "title", "")
        }
    }

    // Button widget
    Component {
        id: buttonWidgetComponent

        Button {
            property var data: ({})
            width: parent.width
            text: root.safeGet(data, "text", "Button")
            onClicked: {
                if (data.action) {
                    console.log("Button clicked:", data.action)
                }
            }
        }
    }

    // Plan widget
    Component {
        id: planWidgetComponent

        PlanWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            planData: data || {}
        }
    }

    // Task widget
    Component {
        id: taskWidgetComponent

        TaskWidget {
            property var data: ({})
            width: parent.width
            taskData: data || {}
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        FileWidget {
            property var data: ({})
            width: parent.width
            filePath: root.safeGet(data, "path", "")
            fileName: root.safeGet(data, "name", "")
            fileSize: root.safeGet(data, "size", 0)
        }
    }

    // Video widget
    Component {
        id: videoWidgetComponent

        VideoWidget {
            property var data: ({})
            width: parent.width
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // Audio widget
    Component {
        id: audioWidgetComponent

        AudioWidget {
            property var data: ({})
            width: parent.width
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // Chart widget
    Component {
        id: chartWidgetComponent

        ChartWidget {
            property var data: ({})
            width: parent.width
            chartData: root.safeGetData(data, data)
            title: root.safeGet(data, "title", "")
            agentColor: root.agentColor
        }
    }

    // Form widget
    Component {
        id: formWidgetComponent

        FormWidget {
            property var data: ({})
            width: parent.width
            formData: root.safeGetData(data, data)
            title: root.safeGet(data, "title", "")
            widgetColor: root.agentColor
        }
    }

    // Step widget
    Component {
        id: stepWidgetComponent

        StepWidget {
            property var data: ({})
            width: parent.width
            stepNumber: root.safeGet(data, "step_number", "")
            stepTitle: root.safeGet(data, "title", "")
            stepDescription: root.safeGet(data, "description", "")
            status: root.safeGet(data, "status", "pending")
            widgetColor: root.agentColor
        }
    }

    // Task list widget
    Component {
        id: taskListWidgetComponent

        TaskListWidget {
            property var data: ({})
            width: parent.width
            tasks: root.safeGet(data, "tasks", [])
            title: root.safeGet(data, "title", "Tasks")
            widgetColor: root.agentColor
        }
    }

    // Skill widget
    Component {
        id: skillWidgetComponent

        SkillWidget {
            property var data: ({})
            width: parent.width
            skillName: root.safeGet(data, "name", "")
            skillDescription: root.safeGet(data, "description", "")
            skillParams: root.safeGet(data, "params", {})
            widgetColor: root.agentColor
        }
    }

    // Error widget (Python sends message in data.error)
    Component {
        id: errorWidgetComponent

        ErrorWidget {
            property var data: ({})
            width: parent ? parent.width : 0
            errorMessage: root.safeGet(data, "error", root.safeGet(data, "message", ""))
            errorType: root.safeGet(data, "type", "Error")
            errorDetails: root.safeGet(data, "details", {})
        }
    }

    // Metadata widget
    Component {
        id: metadataWidgetComponent

        MetadataWidget {
            property var data: ({})
            width: parent.width
            metadata: root.safeGetData(data, data) || {}
            title: root.safeGet(data, "title", "Metadata")
        }
    }
}
