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
            top: parent.top
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

            // Render structured content or plain text
            Loader {
                id: contentLoader
                width: parent.width

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

    // Plain text content component
    Component {
        id: textContentComponent

        Text {
            text: root.content || ""
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

    // Structured content component (renders widgets)
    Component {
        id: structuredContentComponent

        Column {
            spacing: 8
            width: parent.width
            height: childrenRect.height

            Repeater {
                model: root.structuredContent || []

                delegate: Loader {
                    id: widgetLoader
                    width: parent.width

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
                    visible: {
                        var type = modelData.content_type || modelData.type || "text"
                        return type !== "typing"
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
            width: parent.width
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
            active: true
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
            filePath: data.path || data.data?.path || ""
            fileName: data.name || data.data?.name || ""
            fileSize: data.size || data.data?.size || 0
        }
    }
}
