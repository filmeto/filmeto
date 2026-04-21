// Simplified debug test for AgentMessageBubble
import QtQuick 2.15
import QtQuick.Controls 2.15

import "../../../app/ui/chat/qml/components"

ApplicationWindow {
    id: root
    visible: true
    width: 800
    height: 600
    title: "Simple Text Debug Test"

    color: "#1e1e1e"

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "AgentMessageBubble - Text Content Debug"
            color: "#ffffff"
            font.pixelSize: 18
            font.weight: Font.Bold
        }

        // Test 1: Minimal text content
        Rectangle {
            width: parent.width
            height: 200
            color: "#252525"
            border.color: "#444"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: "Test 1: Simple Text (minimal data)"
                    color: "#aaa"
                    font.pixelSize: 12
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test"
                    agentColor: "#4a90e2"
                    agentIcon: "T"
                    structuredContent: [
                        {content_type: "text", data: {text: "Hello World"}}
                    ]
                    timestamp: ""
                    crewMetadata: ({})
                }
            }
        }

        // Test 2: Full data structure
        Rectangle {
            width: parent.width
            height: 200
            color: "#252525"
            border.color: "#444"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: "Test 2: Full data structure"
                    color: "#aaa"
                    font.pixelSize: 12
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test"
                    agentColor: "#4a90e2"
                    agentIcon: "T"
                    structuredContent: [
                        {
                            content_id: "test-1",
                            content_type: "text",
                            data: {text: "This is a test message"},
                            status: "completed"
                        }
                    ]
                    timestamp: "12:00"
                    crewMetadata: ({})
                }
            }
        }

        // Test 3: Multiple content items
        Rectangle {
            width: parent.width
            height: 200
            color: "#252525"
            border.color: "#444"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: "Test 3: Multiple items (text + error)"
                    color: "#aaa"
                    font.pixelSize: 12
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: "Test"
                    agentColor: "#e74c3c"
                    agentIcon: "E"
                    structuredContent: [
                        {content_type: "text", data: {text: "First message"}},
                        {content_type: "error", data: {error: "Error occurred"}}
                    ]
                    timestamp: "12:01"
                    crewMetadata: ({})
                }
            }
        }
    }
}
