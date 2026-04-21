// Test real history data in QML
import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../../app/ui/chat/qml/components"

ApplicationWindow {
    id: root
    visible: true
    width: 800
    height: 600
    title: "Real History Data Test"

    color: "#1e1e1e"

    // Test data - simulates what Python passes to QML
    property var testMessage: {
        "messageId": "test-123",
        "senderId": "test-agent",
        "senderName": "Test Agent",
        "isUser": false,
        "agentColor": "#4a90e2",
        "agentIcon": "🤖",
        "crewMetadata": {},
        "structuredContent": [
            {
                "content_id": "5875070a-dc01-4468-a5f9-29dd2d37a1b2",
                "content_type": "text",
                "title": "Final Response",
                "description": "Test description",
                "data": {
                    "text": "这是一条测试消息。如果能看到这段文字，说明文本提取逻辑工作正常。"
                },
                "metadata": {},
                "status": "creating",
                "parent_id": null
            }
        ],
        "contentType": "text",
        "isRead": true,
        "timestamp": null,
        "dateGroup": ""
    }

    Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "Real History Data Test"
            color: "#ffffff"
            font.pixelSize: 18
            font.weight: Font.Bold
        }

        Text {
            text: "This simulates the data format from Python → QML"
            color: "#aaaaaa"
            font.pixelSize: 12
        }

        Rectangle {
            width: parent.width
            height: 300
            color: "#252525"
            border.color: "#444"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 10

                Text {
                    text: "Message Bubble:"
                    color: "#aaa"
                    font.pixelSize: 12
                }

                AgentMessageBubble {
                    width: parent.width
                    senderName: testMessage.senderName
                    agentColor: testMessage.agentColor
                    agentIcon: testMessage.agentIcon
                    structuredContent: testMessage.structuredContent
                    timestamp: ""
                    crewMetadata: testMessage.crewMetadata

                    Component.onCompleted: {
                        console.log("[QML Test] AgentMessageBubble loaded")
                        console.log("[QML Test] senderName:", senderName)
                        console.log("[QML Test] structuredContent length:", structuredContent.length)
                        if (structuredContent.length > 0) {
                            console.log("[QML Test] First item keys:", Object.keys(structuredContent[0]))
                            console.log("[QML Test] First item data:", JSON.stringify(structuredContent[0]))
                        }
                    }
                }
            }
        }
    }
}
