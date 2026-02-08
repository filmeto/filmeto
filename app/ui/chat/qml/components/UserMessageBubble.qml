// UserMessageBubble.qml - Right-aligned user message bubble with avatar
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var structuredContent: []  // Required: structured content array
    property bool isRead: true
    property string userName: "You"
    property string userIcon: "👤"
    property string timestamp: ""

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"
    readonly property color timestampColor: "#888888"
    readonly property color avatarColor: "#6fa8e8"
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Available width for content (minus avatar space on both sides)
    readonly property int availableWidth: parent.width - totalAvatarWidth

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: headerRow.height + bubbleContainer.height

    Row {
        id: headerRow
        anchors {
            right: parent.right
            rightMargin: 12
            top: parent.top
            topMargin: 12
        }
        spacing: 8
        height: Math.max(avatarRect.height, nameText.implicitHeight)

        // Timestamp (on the left of user name)
        Text {
            id: timestampText
            text: root.timestamp
            color: timestampColor
            font.pixelSize: 11
            anchors.verticalCenter: parent.verticalCenter
            visible: root.timestamp !== ""
        }

        // User name
        Text {
            id: nameText
            text: root.userName
            color: textColor
            font.pixelSize: 13
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
            opacity: 0.9
        }

        // Avatar/icon
        Rectangle {
            id: avatarRect
            width: avatarSize
            height: avatarSize
            radius: width / 2
            color: avatarColor
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.userIcon
                font.pixelSize: 18
            }
        }
    }

    // Message bubble container - renders structured content
    Item {
        id: bubbleContainer
        anchors {
            right: parent.right
            rightMargin: 40  // avatar (32) + spacing (8)
            top: headerRow.bottom
            topMargin: 12
        }
        width: contentColumn.width
        height: contentColumn.height

        // Render structured content items
        Column {
            id: contentColumn
            spacing: 8

            Repeater {
                model: root.structuredContent || []

                delegate: Loader {
                    id: contentLoader
                    width: availableWidth

                    sourceComponent: {
                        var type = modelData.content_type || modelData.type || "text"
                        switch (type) {
                            case "text": return textContentComponent
                            case "code_block": return codeBlockContentComponent
                            // Add more content types as needed for user messages
                            default: return textContentComponent
                        }
                    }

                    property var contentData: modelData
                }
            }
        }
    }

    // Text content component
    Component {
        id: textContentComponent

        Rectangle {
            width: Math.min(availableWidth, contentText.implicitWidth + 24)
            height: contentText.implicitHeight + 24

            color: bubbleColor
            radius: 9

            Text {
                id: contentText
                anchors {
                    fill: parent
                    margins: 12
                }

                text: contentData.data.text || ""
                color: textColor
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
                lineHeight: 1.4
                linkColor: "#87ceeb"

                onLinkActivated: function(link) {
                    Qt.openUrlExternally(link)
                }
            }
        }
    }

    // Code block content component
    Component {
        id: codeBlockContentComponent

        Rectangle {
            width: availableWidth
            height: codeColumn.height + 16

            color: bubbleColor
            radius: 9

            Column {
                id: codeColumn
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 12
                }
                spacing: 8

                // Language label
                Text {
                    text: contentData.language || contentData.data.language || "Code"
                    color: "#ffffff"
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    visible: contentData.language || contentData.data.language
                }

                // Code content
                Text {
                    width: parent.width
                    text: contentData.code || contentData.data.code || ""
                    color: "#ffffff"
                    font.pixelSize: 12
                    font.family: "Consolas, Monaco, monospace"
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
            }
        }
    }
}
