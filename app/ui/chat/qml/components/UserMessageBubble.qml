// UserMessageBubble.qml - Right-aligned user message bubble with avatar
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

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

    // Available width for content (minus avatar space on both sides); never negative
    readonly property int availableWidth: Math.max(0, width - totalAvatarWidth)

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

    // Height calculated from header + bubble content + margins (12 top + 12 gap)
    height: headerRow.height + bubbleContainer.height + 24
    implicitHeight: height

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
                            // Basic content
                            case "text": return userTextBubbleComponent
                            case "code_block": return userCodeBubbleComponent
                            // Media content (user uploads)
                            case "image": return imageWidgetComponent
                            case "video": return videoWidgetComponent
                            case "audio": return audioWidgetComponent
                            // File content
                            case "file_attachment": return fileWidgetComponent
                            case "file": return fileWidgetComponent
                            // Interactive content
                            case "link": return linkWidgetComponent
                            // Metadata content
                            case "metadata": return metadataWidgetComponent
                            // Default fallback
                            default: return userTextBubbleComponent
                        }
                    }

                    property var contentData: modelData

                    onLoaded: {
                        // Pass data to the widget
                        if (item.hasOwnProperty('data')) {
                            item.data = modelData
                        }
                    }
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // User Message Bubble Components (with colored background)
    // ─────────────────────────────────────────────────────────────

    // User text bubble component (with blue background)
    Component {
        id: userTextBubbleComponent

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

                text: root.safeGet(contentData, "text", "")
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

    // User code block bubble component (with blue background)
    Component {
        id: userCodeBubbleComponent

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
                    text: root.safeGet(contentData, "language", "Code")
                    color: "#ffffff"
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    visible: root.safeGet(contentData, "language", "") !== ""
                }

                // Code content
                Text {
                    width: parent.width
                    text: root.safeGet(contentData, "code", "")
                    color: "#ffffff"
                    font.pixelSize: 12
                    font.family: "Consolas, Monaco, monospace"
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Widget Components (shared)
    // ─────────────────────────────────────────────────────────────

    // Image widget
    Component {
        id: imageWidgetComponent

        ImageWidget {
            property var data: ({})
            width: availableWidth
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // Video widget
    Component {
        id: videoWidgetComponent

        VideoWidget {
            property var data: ({})
            width: availableWidth
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // Audio widget
    Component {
        id: audioWidgetComponent

        AudioWidget {
            property var data: ({})
            width: availableWidth
            source: root.safeGet(data, "url", "")
            caption: root.safeGet(data, "caption", "")
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        FileWidget {
            property var data: ({})
            width: availableWidth
            filePath: root.safeGet(data, "path", "")
            fileName: root.safeGet(data, "name", "")
            fileSize: root.safeGet(data, "size", 0)
        }
    }

    // Link widget (for @resource references)
    Component {
        id: linkWidgetComponent

        LinkWidget {
            property var data: ({})
            width: availableWidth
            url: root.safeGet(data, "url", "")
            title: root.safeGet(data, "title", "")
        }
    }

    // Metadata widget
    Component {
        id: metadataWidgetComponent

        MetadataWidget {
            property var data: ({})
            width: availableWidth
            metadata: root.safeGetData(data, data) || {}
            title: root.safeGet(data, "title", "Metadata")
        }
    }
}
