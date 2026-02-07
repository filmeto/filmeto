// AgentMessageBubble.qml - Left-aligned agent message with avatar and metadata
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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

    implicitWidth: parent.width
    implicitHeight: mainColumn.implicitHeight

    // Main layout
    ColumnLayout {
        id: mainColumn
        anchors {
            left: parent.left
            right: parent.right
        }
        spacing: 4

        // Header row with avatar and name
        RowLayout {
            spacing: 8
            Layout.fillWidth: false

            // Avatar/icon
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

            // Agent name
            ColumnLayout {
                spacing: 0

                Text {
                    text: root.senderName
                    color: nameColor
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                // Crew title if available
                Text {
                    visible: root.crewMetadata && root.crewMetadata.crew_title
                    text: root.crewMetadata.crew_title || ""
                    color: timestampColor
                    font.pixelSize: 11
                }
            }
        }

        // Message content area
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredWidth: Math.min(parent.width, 700)
            Layout.maximumWidth: 700

            color: backgroundColor
            radius: 12

            // Content column
            ColumnLayout {
                anchors {
                    fill: parent
                    margins: 12
                }
                spacing: 8

                // Render structured content or plain text
                Loader {
                    id: contentLoader
                    Layout.fillWidth: true
                    sourceComponent: {
                        if (root.structuredContent && root.structuredContent.length > 0) {
                            return structuredContentComponent
                        } else {
                            return textContentComponent
                        }
                    }
                }
            }
        }
    }

    // Plain text content component
    Component {
        id: textContentComponent

        Text {
            text: root.content || ""
            color: textColor
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            textFormat: Text.MarkdownText
            lineHeight: 1.5
            linkColor: "#87ceeb"

            Layout.fillWidth: true

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

    // Structured content component (renders widgets)
    Component {
        id: structuredContentComponent

        ColumnLayout {
            spacing: 8

            Repeater {
                model: root.structuredContent || []

                delegate: Loader {
                    id: widgetLoader
                    Layout.fillWidth: true

                    sourceComponent: {
                        var type = modelData.content_type || modelData.type || "text"
                        switch (type) {
                            case "text": return textWidgetComponent
                            case "code_block": return codeBlockComponent
                            case "thinking": return thinkingWidgetComponent
                            case "tool_call": return toolCallComponent
                            case "tool_response": return toolResponseComponent
                            case "typing": return typingIndicatorComponent
                            case "progress": return progressWidgetComponent
                            case "image": return imageWidgetComponent
                            case "table": return tableWidgetComponent
                            case "link": return linkWidgetComponent
                            case "button": return buttonWidgetComponent
                            case "plan": return planWidgetComponent
                            case "task": return taskWidgetComponent
                            case "file": return fileWidgetComponent
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
            Layout.fillWidth: true
        }
    }

    // Code block widget
    Component {
        id: codeBlockComponent

        CodeBlockWidget {
            property var data: ({})
            Layout.fillWidth: true
            code: data.code || data.data?.code || ""
            language: data.language || data.data?.language || "text"
        }
    }

    // Thinking widget (collapsible)
    Component {
        id: thinkingWidgetComponent

        ThinkingWidget {
            property var data: ({})
            Layout.fillWidth: true
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
            Layout.fillWidth: true
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
            Layout.fillWidth: true
            toolName: data.tool_name || data.data?.tool_name || ""
            response: data.response || data.data?.response || ""
            isError: data.is_error || data.data?.is_error || false
        }
    }

    // Typing indicator widget
    Component {
        id: typingIndicatorComponent

        TypingIndicator {
            Layout.fillWidth: true
            active: true
        }
    }

    // Progress widget
    Component {
        id: progressWidgetComponent

        ProgressWidget {
            property var data: ({})
            Layout.fillWidth: true
            widgetColor: root.agentColor
            text: data.progress || data.data?.progress || ""
            percentage: data.percentage || data.data?.percentage || null
        }
    }

    // Image widget
    Component {
        id: imageWidgetComponent

        ImageWidget {
            property var data: ({})
            Layout.fillWidth: true
            source: data.url || data.data?.url || ""
            caption: data.caption || data.data?.caption || ""
        }
    }

    // Table widget
    Component {
        id: tableWidgetComponent

        TableWidget {
            property var data: ({})
            Layout.fillWidth: true
            tableData: data.data || {}
        }
    }

    // Link widget
    Component {
        id: linkWidgetComponent

        LinkWidget {
            property var data: ({})
            Layout.fillWidth: true
            url: data.url || data.data?.url || ""
            title: data.title || data.data?.title || ""
        }
    }

    // Button widget
    Component {
        id: buttonWidgetComponent

        Button {
            property var data: ({})
            Layout.fillWidth: false
            text: data.text || data.data?.text || "Button"
            onClicked: {
                if (data.action) {
                    // Handle button action via signal or callback
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
            Layout.fillWidth: true
            widgetColor: root.agentColor
            planData: data
        }
    }

    // Task widget
    Component {
        id: taskWidgetComponent

        TaskWidget {
            property var data: ({})
            Layout.fillWidth: true
            taskData: data
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        FileWidget {
            property var data: ({})
            Layout.fillWidth: true
            filePath: data.path || data.data?.path || ""
            fileName: data.name || data.data?.name || ""
            fileSize: data.size || data.data?.size || 0
        }
    }
}
