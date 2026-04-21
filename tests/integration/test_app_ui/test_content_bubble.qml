// Test interface for AgentMessageBubble with various content types
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../../../app/ui/chat/qml/components"

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 800
    title: qsTr("AgentMessageBubble Content Test")

    color: "#1e1e1e"

    function getContentTypeString(contentArray) {
        if (!contentArray || contentArray.length === 0) return "none"
        var types = []
        for (var i = 0; i < contentArray.length; i++) {
            if (contentArray[i].content_type) {
                types.push(contentArray[i].content_type)
            }
        }
        return types.join(", ")
    }

    function getContentCount(contentArray) {
        return contentArray ? contentArray.length : 0
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: 20
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 30

            // Title
            Text {
                text: "AgentMessageBubble Content Display Test"
                color: "#ffffff"
                font.pixelSize: 24
                font.weight: Font.Bold
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 20
            }

            // Description
            Text {
                text: "Testing various content types in AgentMessageBubble component"
                color: "#aaaaaa"
                font.pixelSize: 14
                Layout.alignment: Qt.AlignHCenter
            }

            // ===== Simple Text =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Simple Text"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test Agent"
                    agentColor: "#4a90e2"
                    agentIcon: "🤖"
                    structuredContent: [
                        {content_id: "text-1", content_type: "text", data: {text: "This is a simple text message."}, status: "completed"}
                    ]
                    timestamp: "12:00 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText1.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText1
                        anchors.centerIn: parent
                        text: "Content items: " + getContentCount(structuredContent) + " | Types: " + getContentTypeString(structuredContent)
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Long Text =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Long Text (wrapping)"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test Agent"
                    agentColor: "#4a90e2"
                    agentIcon: "🤖"
                    structuredContent: [
                        {content_id: "text-2", content_type: "text", data: {text: "This is a much longer text message that should wrap across multiple lines. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."}, status: "completed"}
                    ]
                    timestamp: "12:01 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText2.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText2
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: text"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Error =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Error Content"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Error Agent"
                    agentColor: "#e74c3c"
                    agentIcon: "⚠️"
                    structuredContent: [
                        {content_id: "error-1", content_type: "error", data: {error: "Something went wrong!", error_type: "RuntimeError"}, status: "completed"}
                    ]
                    timestamp: "12:02 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText3.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText3
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: error"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Thinking =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Thinking Content"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test Agent"
                    agentColor: "#9b59b6"
                    agentIcon: "🧠"
                    structuredContent: [
                        {content_id: "thinking-1", content_type: "thinking", data: {thought: "Let me analyze this problem step by step..."}, status: "completed"}
                    ]
                    timestamp: "12:03 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText4.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText4
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: thinking"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Code Block =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Code Block"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Code Agent"
                    agentColor: "#27ae60"
                    agentIcon: "💻"
                    structuredContent: [
                        {content_id: "code-1", content_type: "code_block", data: {code: "def hello():\n    print('Hello, World!')\n    return True", language: "python"}, status: "completed"}
                    ]
                    timestamp: "12:04 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText5.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText5
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: code_block"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Tool Call =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Tool Call"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Tool Agent"
                    agentColor: "#f39c12"
                    agentIcon: "🔧"
                    structuredContent: [
                        {content_id: "tool-1", content_type: "tool_call", data: {tool_name: "search_files", tool_args: {pattern: "*.py", path: "/src"}}, status: "completed"}
                    ]
                    timestamp: "12:05 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText6.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText6
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: tool_call"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Tool Response =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Tool Response"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Tool Agent"
                    agentColor: "#16a085"
                    agentIcon: "✅"
                    structuredContent: [
                        {content_id: "tool-response-1", content_type: "tool_response", data: {tool_name: "search_files", response: "Found 42 files matching pattern."}, status: "completed"}
                    ]
                    timestamp: "12:06 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText7.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText7
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: tool_response"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Progress =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Progress"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Progress Agent"
                    agentColor: "#3498db"
                    agentIcon: "📊"
                    structuredContent: [
                        {content_id: "progress-1", content_type: "progress", data: {progress: "Processing file...", percentage: 75}, status: "completed"}
                    ]
                    timestamp: "12:07 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText8.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText8
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: progress"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Typing Indicator =====
            Column {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Typing Indicator"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Typing Agent"
                    agentColor: "#95a5a6"
                    agentIcon: "✍️"
                    structuredContent: [
                        {content_id: "typing-1", content_type: "typing", data: {}}
                    ]
                    timestamp: "12:08 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText9.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText9
                        anchors.centerIn: parent
                        text: "Content items: 1 | Types: typing (should be hidden)"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }

            // ===== Multiple Content Types =====
            Column {
                Layout.fillWidth: true
                spacing: 10
                Layout.bottomMargin: 40

                Rectangle {
                    width: parent.width
                    height: 40
                    color: "#2d2d2d"
                    radius: 8

                    Text {
                        anchors.centerIn: parent
                        text: "Multiple Content Types"
                        color: "#ffffff"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                    }
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Multi Agent"
                    agentColor: "#e67e22"
                    agentIcon: "🎯"
                    structuredContent: [
                        {content_id: "multi-1", content_type: "text", data: {text: "First, let me think about this..."}, status: "completed"},
                        {content_id: "multi-2", content_type: "thinking", data: {thought: "Analyzing the requirements and planning the approach."}, status: "completed"},
                        {content_id: "multi-3", content_type: "tool_call", data: {tool_name: "calculate", tool_args: {expression: "2+2"}}, status: "completed"},
                        {content_id: "multi-4", content_type: "tool_response", data: {tool_name: "calculate", response: "Result: 4"}, status: "completed"},
                        {content_id: "multi-5", content_type: "text", data: {text: "The answer is 4!"}, status: "completed"}
                    ]
                    timestamp: "12:09 PM"
                    crewMetadata: ({})
                }

                Rectangle {
                    width: parent.width
                    height: debugText10.implicitHeight + 20
                    color: "#252525"
                    radius: 6

                    Text {
                        id: debugText10
                        anchors.centerIn: parent
                        text: "Content items: 5 | Types: text, thinking, tool_call, tool_response, text"
                        color: "#888888"
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
