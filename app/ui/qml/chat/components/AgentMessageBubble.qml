// AgentMessageBubble.qml - Left-aligned agent message with avatar and metadata
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

Item {
    id: root

    property string senderName: ""
    property string content: ""
    property color agentColor: "#4a90e2"
    property string agentIcon: "🤖"
    property var crewMetadata: ({})
    property var structuredContent: []

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color backgroundColor: "#353535"
    readonly property color textColor: "#e0e0e0"
    readonly property color nameColor: agentColor
    readonly property color timestampColor: "#808080"

    // Avatar dimensions
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Available width for content (minus avatar space on both sides)
    readonly property int availableWidth: parent.width - totalAvatarWidth

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: headerRow.height + contentRect.implicitHeight + 8

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
        height: Math.max(avatarRect.height, nameColumn.implicitHeight)

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

            Text {
                text: root.senderName
                color: nameColor
                font.pixelSize: 13
                font.weight: Font.Medium
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

    // Message content area - aligned with avatar
    Rectangle {
        id: contentRect
        anchors {
            left: parent.left
            leftMargin: 40  // avatar (32) + spacing (8)
            top: headerRow.bottom
            topMargin: 12
        }
        width: availableWidth
        implicitHeight: contentColumn.implicitHeight + 24
        color: backgroundColor
        radius: 6

        // Content column
        Column {
            id: contentColumn
            anchors {
                left: parent.left
                right: parent.right
                top: parent.top
                margins: 12
            }
            spacing: 8

                    // Always render through structured content
            Loader {
                id: contentLoader
                width: parent.width
                sourceComponent: structuredContentComponent
            }
        }
    }

    // Structured content component (renders widgets)
    Component {
        id: structuredContentComponent

        Column {
            id: contentColumn
            spacing: 8
            width: parent.width
            height: childrenRect.height

            // Use a computed property that always has at least one item
            property var effectiveStructuredContent: {
                if (root.structuredContent && root.structuredContent.length > 0) {
                    return root.structuredContent
                }
                // Fallback: convert content to a simple text item
                return [{ content_type: "text", text: root.content || "" }]
            }

            // Filter out non-typing content
            property var nonTypingContent: {
                var items = []
                for (var i = 0; i < effectiveStructuredContent.length; i++) {
                    var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
                    if (type !== "typing") {
                        items.push(effectiveStructuredContent[i])
                    }
                }
                return items.length > 0 ? items : [{ content_type: "text", text: "" }]
            }

            // Filter typing content (always last)
            property var typingContent: {
                var items = []
                for (var i = 0; i < effectiveStructuredContent.length; i++) {
                    var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
                    if (type === "typing") {
                        items.push(effectiveStructuredContent[i])
                    }
                }
                return items
            }

            // Non-typing content (displayed first)
            Repeater {
                model: nonTypingContent

                delegate: Loader {
                    id: widgetLoader
                    width: parent.width

                    sourceComponent: {
                        var type = modelData.content_type || modelData.type || "text"
                        switch (type) {
                            // Basic content
                            case "text": return textWidgetComponent
                            case "code_block": return codeBlockComponent

                            // Thinking content
                            case "thinking": return thinkingWidgetComponent

                            // Tool content
                            case "tool_call": return toolCallComponent
                            case "tool_response": return toolResponseComponent

                            // Media content
                            case "image": return imageWidgetComponent
                            case "video": return videoWidgetComponent
                            case "audio": return audioWidgetComponent

                            // Data display
                            case "table": return tableWidgetComponent
                            case "chart": return chartWidgetComponent

                            // Interactive elements
                            case "link": return linkWidgetComponent
                            case "button": return buttonWidgetComponent
                            case "form": return formWidgetComponent

                            // Files
                            case "file_attachment":
                            case "file": return fileWidgetComponent

                            // Tasks and plans
                            case "plan": return planWidgetComponent
                            case "task_list":
                            case "task": return taskWidgetComponent
                            case "step": return stepWidgetComponent
                            case "skill": return skillWidgetComponent

                            // Status and metadata
                            case "progress": return progressWidgetComponent
                            case "todo_write": return todoWriteWidgetComponent
                            case "metadata": return metadataWidgetComponent
                            case "error": return errorWidgetComponent
                            case "llm_output": return llmOutputComponent

                            default: return textWidgetComponent
                        }
                    }

                    property var widgetData: modelData

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

            // Typing indicators (always displayed last)
            Repeater {
                model: typingContent

                delegate: Loader {
                    id: typingLoader
                    width: parent.width
                    sourceComponent: typingIndicatorComponent

                    property var widgetData: modelData

                    onLoaded: {
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

    // Text widget
    Component {
        id: textWidgetComponent

        Text {
            property var data: ({})
            text: data.text || data.data?.text || ""
            color: textColor
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            lineHeight: 1.5
            linkColor: "#87ceeb"
            width: parent.width

            onLinkActivated: function(link) {
                // Handle reference links like ref://tool_call:abc123
                if (link.startsWith("ref://")) {
                    var parts = link.substring(6).split(":")
                    if (parts.length >= 2) {
                        root.referenceClicked(parts[0], parts[1])
                    }
                } else {
                    Qt.openUrlExternally(link)
                }
            }
        }
    }

    // Code block widget
    Component {
        id: codeBlockComponent

        CodeBlockWidget {
            property var data: ({})
            width: parent.width
            code: data.code || data.data?.code || ""
            language: data.language || data.data?.language || "text"
        }
    }

    // Thinking widget (collapsible)
    Component {
        id: thinkingWidgetComponent

        ThinkingWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            thought: data.thought || data.data?.thought || ""
            title: data.title || data.data?.title || "Thinking Process"
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
            toolName: data.tool_name || data.data?.tool_name || ""
            toolArgs: data.tool_args || data.data?.tool_args || {}
        }
    }

    // Tool response widget
    Component {
        id: toolResponseComponent

        ToolResponseWidget {
            property var data: ({})
            width: parent.width
            toolName: data.tool_name || data.data?.tool_name || ""
            response: data.response || data.data?.response || ""
            isError: data.is_error || data.data?.is_error || false
        }
    }

    // Typing indicator widget
    Component {
        id: typingIndicatorComponent

        TypingIndicator {
            property var widgetColor: "#4a90e2"
            active: true
            dotColor: widgetColor
        }
    }

    // Progress widget
    Component {
        id: progressWidgetComponent

        ProgressWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            text: data.progress || data.data?.progress || ""
            percentage: data.percentage || data.data?.percentage || null
        }
    }

    // TodoWrite widget
    Component {
        id: todoWriteWidgetComponent

        TodoWriteWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            todoData: data
        }
    }

    // Image widget
    Component {
        id: imageWidgetComponent

        ImageWidget {
            property var data: ({})
            width: parent.width
            source: data.url || data.data?.url || ""
            caption: data.caption || data.data?.caption || ""
        }
    }

    // Table widget
    Component {
        id: tableWidgetComponent

        TableWidget {
            property var data: ({})
            width: parent.width
            tableData: data.data || {}
        }
    }

    // Link widget
    Component {
        id: linkWidgetComponent

        LinkWidget {
            property var data: ({})
            width: parent.width
            url: data.url || data.data?.url || ""
            title: data.title || data.data?.title || ""
        }
    }

    // Button widget
    Component {
        id: buttonWidgetComponent

        Button {
            property var data: ({})
            text: data.text || data.data?.text || "Button"
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
            planData: data
        }
    }

    // Task widget
    Component {
        id: taskWidgetComponent

        TaskWidget {
            property var data: ({})
            width: parent.width
            taskData: data
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        FileWidget {
            property var data: ({})
            width: parent.width
            filePath: data.path || (data.data && data.data.path) ? data.data.path : ""
            fileName: data.name || (data.data && data.data.name) ? data.data.name : ""
            fileSize: data.size || (data.data && data.data.size) ? data.data.size : 0
        }
    }

    // Video widget
    Component {
        id: videoWidgetComponent

        VideoWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            source: (data.data && data.data.url) ? data.data.url : ""
            caption: data.description || ""
        }
    }

    // Audio widget
    Component {
        id: audioWidgetComponent

        AudioWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            source: (data.data && data.data.url) ? data.data.url : ""
            caption: data.description || ""
        }
    }

    // Chart widget
    Component {
        id: chartWidgetComponent

        ChartWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            chartType: (data.data && data.data.chart_type) ? data.data.chart_type : "bar"
            chartData: (data.data && data.data.data) ? data.data.data : {}
            title: data.title || ""
        }
    }

    // Form widget
    Component {
        id: formWidgetComponent

        FormWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            formData: data.data || {}
        }
    }

    // Step widget
    Component {
        id: stepWidgetComponent

        StepWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            stepData: ({
                title: data.title || "",
                description: data.description || "",
                status: (data.data && data.data.status) ? data.data.status : "pending",
                step_number: (data.data && data.data.step_number) ? data.data.step_number : 0
            })
        }
    }

    // Skill widget
    Component {
        id: skillWidgetComponent

        SkillWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            skillData: ({
                name: (data.data && data.data.skill_name) ? data.data.skill_name : (data.title || ""),
                status: data.status || "pending",
                progress: 0
            })
        }
    }

    // Metadata widget
    Component {
        id: metadataWidgetComponent

        MetadataWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            metadataData: ({
                metadata_type: (data.data && data.data.metadata_type) ? data.data.metadata_type : (data.title || ""),
                title: data.title || "",
                description: data.description || "",
                metadata_data: (data.data && data.data.data) ? data.data.data : ({})
            })
        }
    }

    // Error widget
    Component {
        id: errorWidgetComponent

        ErrorWidget {
            property var data: ({})
            width: parent.width
            errorData: ({
                error_message: (data.data && data.data.error) ? data.data.error : "",
                error_type: (data.data && data.data.error_type) ? data.data.error_type : (data.title || "Error"),
                details: data.description || ""
            })
        }
    }

    // LLM output widget (collapsible)
    Component {
        id: llmOutputComponent

        LlmOutputWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.agentColor
            output: data.output || data.data?.output || ""
            title: data.title || data.data?.title || "LLM Output"
        }
    }
}
