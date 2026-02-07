// AgentChatList.qml - Main QML chat list with proper layout
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ListView {
    id: root

    // Signals
    signal loadMoreRequested()
    signal referenceClicked(string refType, string refId)
    signal messageCompleted(string messageId, string agentName)

    // Configuration
    width: 400
    height: 600
    spacing: 4

    // Model from Python (via contextProperty)
    model: _chatModel

    // Smooth scrolling
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    cacheBuffer: height * 2
    clip: true

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#252525"
        z: -1
    }

    // Main delegate
    delegate: Item {
        id: delegateItem
        width: root.width

        // Calculate height based on content
        readonly property bool isUser: model.isUser || false
        readonly property bool isTypingOnly: (model.contentType || "") === "typing"

        height: isUser ? userContentColumn.height + 16 : agentContentColumn.height + 16

        // ===== USER MESSAGE (Right-aligned) =====
        Item {
            id: userContentColumn
            anchors {
                right: parent.right
                left: parent.horizontalCenter
                rightMargin: 10
                leftMargin: 10
            }
            width: parent.width * 0.7
            visible: delegateItem.isUser

            // Blue bubble on the right
            Rectangle {
                anchors.right: parent.right
                width: Math.min(userText.implicitWidth + 24, parent.width)
                height: userText.implicitHeight + 24
                color: "#4a90e2"
                radius: 18

                Text {
                    id: userText
                    anchors {
                        fill: parent
                        margins: 12
                    }
                    text: model.content || ""
                    color: "#ffffff"
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                }
            }
        }

        // ===== AGENT MESSAGE (Left-aligned) =====
        Column {
            id: agentContentColumn
            visible: !delegateItem.isUser
            width: parent.width
            spacing: 6

            // Add top margin
            Item { width: 1; height: 8 }

            // Main row: avatar + content
            Row {
                width: parent.width
                spacing: 8

                // Avatar (42x42 rounded rect)
                Rectangle {
                    width: 42
                    height: 42
                    radius: 6
                    color: model.agentColor || "#4a90e2"

                    Text {
                        anchors.centerIn: parent
                        text: model.agentIcon || "🤖"
                        font.pixelSize: 20
                    }
                }

                // Content area
                Column {
                    width: parent.width - 50
                    spacing: 6

                    // Name row with optional crew title
                    Row {
                        spacing: 8

                        Text {
                            text: model.senderName || ""
                            color: model.agentColor || "#4a90e2"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        // Crew title badge
                        Rectangle {
                            visible: model.crewMetadata && model.crewMetadata.crew_title
                            width: crewTitleText.implicitWidth + 16
                            height: 18
                            radius: 3
                            color: model.agentColor || "#4a90e2"

                            Text {
                                id: crewTitleText
                                anchors.centerIn: parent
                                text: (model.crewMetadata && model.crewMetadata.crew_title) || ""
                                color: "white"
                                font.pixelSize: 9
                                font.bold: true
                            }
                        }
                    }

                    // Content area - render structured content or plain text
                    Item {
                        width: parent.width
                        height: contentLoader.height + 16

                        // Background bubble
                        Rectangle {
                            anchors.fill: parent
                            color: "#2b2d30"
                            radius: 5
                            visible: !delegateItem.isTypingOnly
                        }

                        // Content loader
                        Loader {
                            id: contentLoader
                            anchors {
                                fill: parent
                                margins: 10
                            }
                            sourceComponent: {
                                var sc = model.structuredContent || []
                                if (sc.length > 0) {
                                    // Has structured content
                                    for (var i = 0; i < sc.length; i++) {
                                        var type = sc[i].content_type || sc[i].type || "text"
                                        if (type === "text" && sc[i].data && sc[i].data.text) {
                                            return textContentComponent
                                        } else if (type === "typing") {
                                            continue
                                        } else if (type === "thinking" || type === "tool_call" || type === "tool_response" || type === "code_block" || type === "progress") {
                                            return structuredContentComponent
                                        }
                                    }
                                }
                                // No structured content, use plain text
                                return textContentComponent
                            }

                            property var modelData: model
                        }
                    }

                    // Typing indicator
                    Row {
                        spacing: 4
                        visible: delegateItem.isTypingOnly

                        Repeater {
                            model: 3
                            Rectangle {
                                width: 8
                                height: 8
                                radius: 4
                                color: model.agentColor || "#4a90e2"

                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    running: true
                                    NumberAnimation { to: 0.3; duration: 400 }
                                    NumberAnimation { to: 1.0; duration: 400 }
                                }
                            }
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
            text: Loader.item.modelData.content || ""
            color: "#e1e1e1"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            width: parent.width
        }
    }

    // Structured content component
    Component {
        id: structuredContentComponent

        Column {
            width: parent.width
            spacing: 4

            Repeater {
                model: Loader.item.modelData.structuredContent || []

                delegate: Item {
                    width: parent.width
                    height: contentText.height + 4

                    property var itemData: modelData

                    Text {
                        id: contentText
                        width: parent.width
                        color: "#e1e1e1"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                        textFormat: Text.PlainText

                        text: {
                            var type = itemData.content_type || itemData.type || "text"
                            var data = itemData.data || {}

                            if (type === "text") {
                                return data.text || ""
                            } else if (type === "thinking") {
                                return "💭 " + (data.thought || "")
                            } else if (type === "tool_call") {
                                return "🔧 " + (data.tool_name || "")
                            } else if (type === "tool_response") {
                                return "✓ " + (data.response || "").substring(0, 100)
                            } else if (type === "code_block") {
                                return "```" + (data.language || "") + "\n" + (data.code || "").substring(0, 100) + "\n```"
                            } else if (type === "progress") {
                                return "⏳ " + (data.progress || "")
                            } else {
                                return "[" + type + "]"
                            }
                        }
                    }
                }
            }
        }
    }

    // Scrollbar
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        contentItem: Rectangle {
            implicitWidth: 10
            radius: width / 2
            color: parent.pressed ? "#606264" :
                   parent.hovered ? "#606264" : "#505254"
            opacity: parent.active ? 1.0 : 0.5

            Behavior on opacity {
                NumberAnimation { duration: 150 }
            }
        }
        background: Rectangle {
            color: "#2b2d30"
            implicitWidth: 10
        }
    }

    // Load more trigger at top
    onAtYBeginningChanged: {
        if (atYBeginning) {
            root.loadMoreRequested()
        }
    }

    // Public method to scroll to bottom
    function scrollToBottom() {
        positionViewAtEnd()
    }
}
