// StructuredContentRenderer.qml - Reusable component for rendering structured message content
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // Input data
    property var structuredContent: []
    property string content: ""

    // Styling
    property color textColor: "#e0e0e0"
    property color widgetColor: "#4a90e2"

    // Widget type support: "full" for all widgets, "basic" for user messages
    property string widgetSupport: "full"

    // Signals
    signal referenceClicked(string refType, string refId)

    implicitHeight: contentColumn.height

    // Effective structured content (fallback to text if no structured content)
    property var effectiveStructuredContent: {
        if (root.structuredContent && root.structuredContent.length > 0) {
            return root.structuredContent
        }
        return [{ content_type: "text", text: root.content || "" }]
    }

    // Filter out non-typing content
    property var nonTypingContent: {
        if (widgetSupport !== "full") {
            return effectiveStructuredContent
        }
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
        if (widgetSupport !== "full") {
            return []
        }
        var items = []
        for (var i = 0; i < effectiveStructuredContent.length; i++) {
            var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
            if (type === "typing") {
                items.push(effectiveStructuredContent[i])
            }
        }
        return items
    }

    Column {
        id: contentColumn
        spacing: 8
        width: parent.width
        // Don't set height - let it be determined by children

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

                        // Thinking content (full support only)
                        case "thinking": return widgetSupport === "full" ? thinkingWidgetComponent : textWidgetComponent

                        // Tool content (full support only)
                        case "tool_call": return widgetSupport === "full" ? toolCallComponent : textWidgetComponent
                        case "tool_response": return widgetSupport === "full" ? toolResponseComponent : textWidgetComponent

                        // Media content
                        case "image": return imageWidgetComponent
                        case "video": return widgetSupport === "full" ? videoWidgetComponent : textWidgetComponent
                        case "audio": return widgetSupport === "full" ? audioWidgetComponent : textWidgetComponent

                        // Data display (full support only)
                        case "table": return widgetSupport === "full" ? tableWidgetComponent : textWidgetComponent
                        case "chart": return widgetSupport === "full" ? chartWidgetComponent : textWidgetComponent

                        // Interactive elements
                        case "link": return linkWidgetComponent
                        case "button": return widgetSupport === "full" ? buttonWidgetComponent : textWidgetComponent
                        case "form": return widgetSupport === "full" ? formWidgetComponent : textWidgetComponent

                        // Files
                        case "file_attachment":
                        case "file": return fileWidgetComponent

                        // Tasks and plans (full support only)
                        case "plan": return widgetSupport === "full" ? planWidgetComponent : textWidgetComponent
                        case "task_list":
                        case "task": return widgetSupport === "full" ? taskWidgetComponent : textWidgetComponent
                        case "step": return widgetSupport === "full" ? stepWidgetComponent : textWidgetComponent
                        case "skill": return widgetSupport === "full" ? skillWidgetComponent : textWidgetComponent

                        // Status and metadata (full support only)
                        case "progress": return widgetSupport === "full" ? progressWidgetComponent : textWidgetComponent
                        case "todo_write": return widgetSupport === "full" ? todoWriteWidgetComponent : textWidgetComponent
                        case "metadata": return widgetSupport === "full" ? metadataWidgetComponent : textWidgetComponent
                        case "error": return widgetSupport === "full" ? errorWidgetComponent : textWidgetComponent
                        case "llm_output": return widgetSupport === "full" ? llmOutputComponent : textWidgetComponent

                        default: return textWidgetComponent
                    }
                }

                property var widgetData: modelData
                property var loadedItem: null

                onLoaded: {
                    loadedItem = item
                    if (item.hasOwnProperty('data')) {
                        item.data = modelData
                    }
                    if (item.hasOwnProperty('widgetColor')) {
                        item.widgetColor = root.widgetColor
                    }
                }

                // Bind height to item's implicitHeight, updates when item's height changes
                height: loadedItem ? (loadedItem.implicitHeight || loadedItem.height || 0) : 0
            }
        }

        // Typing indicators (always displayed last, full support only)
        Repeater {
            model: typingContent

            delegate: Loader {
                id: typingLoader
                width: parent.width
                sourceComponent: typingIndicatorComponent

                property var widgetData: modelData
                property var loadedItem: null

                onLoaded: {
                    loadedItem = item
                    if (item.hasOwnProperty('widgetColor')) {
                        item.widgetColor = root.widgetColor
                    }
                }

                height: loadedItem ? (loadedItem.implicitHeight || loadedItem.height || 0) : 0
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
            lineHeight: widgetSupport === "full" ? 1.5 : 1.4
            linkColor: "#87ceeb"
            width: parent.width

            onLinkActivated: function(link) {
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            property var widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
            formData: data.data || {}
        }
    }

    // Step widget
    Component {
        id: stepWidgetComponent

        StepWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
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
            widgetColor: root.widgetColor
            output: data.output || data.data?.output || ""
            title: data.title || data.data?.title || "LLM Output"
        }
    }
}
