// UserMessageBubble.qml - Right-aligned user message bubble with avatar
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string content: ""
    property bool isRead: true
    property string userName: "You"
    property string userIcon: "👤"
    property var structuredContent: []

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"
    readonly property color avatarColor: "#6fa8e8"
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Internal bubble padding
    readonly property int bubblePadding: 12

    // Available width for bubble (total width minus avatar space on both sides)
    readonly property int availableWidth: Math.max(80, width - totalAvatarWidth)

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: 12 + headerRow.height + 12 + bubbleContainer.height + 8

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

        // User name (first element, placed on left in normal layout)
        Text {
            id: nameText
            text: root.userName
            color: textColor
            font.pixelSize: 13
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
            opacity: 0.9
        }

        // Avatar/icon (second element, placed on right)
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

    // Message bubble container positioned on the right
    Item {
        id: bubbleContainer
        anchors {
            right: parent.right
            rightMargin: avatarSize + avatarSpacing  // avatar space on the right side
            top: headerRow.bottom
            topMargin: 12
        }
        width: bubble.width
        height: bubble.height

        // Message bubble — width adapts to content, max = availableWidth
        Rectangle {
            id: bubble
            width: Math.min(Math.max(80, structuredContentColumn.implicitWidth + bubblePadding * 2), availableWidth)
            height: structuredContentColumn.implicitHeight + bubblePadding * 2

            color: bubbleColor
            radius: 9

            // Always render through structured content
            Column {
                id: structuredContentColumn
                x: bubblePadding
                y: bubblePadding
                // Width follows bubble minus padding; adapts when bubble resizes
                width: bubble.width - bubblePadding * 2
                spacing: 8

                // Use a computed property that always has at least one item
                property var effectiveStructuredContent: {
                    if (root.structuredContent && root.structuredContent.length > 0) {
                        return root.structuredContent
                    }
                    // Fallback: convert content to a simple text item
                    return [{ content_type: "text", text: root.content || "" }]
                }

                Repeater {
                    model: structuredContentColumn.effectiveStructuredContent

                    delegate: Loader {
                        id: widgetLoader
                        width: structuredContentColumn.width
                        // Propagate loaded item's implicitWidth so the Column
                        // reports a correct implicitWidth for bubble sizing
                        implicitWidth: item ? item.implicitWidth : 0

                        sourceComponent: {
                            var type = modelData.content_type || modelData.type || "text"
                            switch (type) {
                                case "text": return textWidgetComponent
                                case "code_block": return codeBlockComponent
                                case "image": return imageWidgetComponent
                                case "link": return linkWidgetComponent
                                case "file_attachment":
                                case "file": return fileWidgetComponent
                                default: return textWidgetComponent
                            }
                        }

                        property var widgetData: modelData

                        onLoaded: {
                            if (item.hasOwnProperty('data')) {
                                item.data = modelData
                            }
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
            lineHeight: 1.4
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

    // Code block widget (simplified for user messages)
    Component {
        id: codeBlockComponent

        Rectangle {
            property var data: ({})
            width: parent.width
            color: "#2a2a2a"
            radius: 4

            Column {
                anchors {
                    fill: parent
                    margins: 8
                }
                spacing: 4

                Text {
                    text: (data.language || data.data?.language || "text").toUpperCase()
                    color: "#888888"
                    font.pixelSize: 10
                    font.weight: Font.Bold
                }

                Text {
                    text: data.code || data.data?.code || ""
                    color: "#e0e0e0"
                    font.pixelSize: 12
                    font.family: "monospace"
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
            }
        }
    }

    // Image widget
    Component {
        id: imageWidgetComponent

        Column {
            property var data: ({})
            width: parent.width
            spacing: 4

            Image {
                width: Math.min(parent.width, 300)
                height: width * 0.75
                source: data.url || data.data?.url || ""
                fillMode: Image.PreserveAspectCrop
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: data.caption || data.data?.caption || ""
                color: "#cccccc"
                font.pixelSize: 11
                font.italic: true
                anchors.horizontalCenter: parent.horizontalCenter
                visible: text !== ""
            }
        }
    }

    // Link widget
    Component {
        id: linkWidgetComponent

        Text {
            property var data: ({})
            text: "<a href=\"" + (data.url || data.data?.url || "") + "\">" +
                  (data.title || data.data?.title || data.url || data.data?.url || "Link") +
                  "</a>"
            color: textColor
            font.pixelSize: 14
            textFormat: Text.RichText
            linkColor: "#87ceeb"
            width: parent.width

            onLinkActivated: function(link) {
                Qt.openUrlExternally(link)
            }
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        Row {
            property var data: ({})
            spacing: 8

            Rectangle {
                width: 40
                height: 40
                color: "#ffffff"
                radius: 4
                opacity: 0.2

                Text {
                    anchors.centerIn: parent
                    text: "📄"
                    font.pixelSize: 20
                }
            }

            Column {
                spacing: 2
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    text: data.name || data.data?.name || "File"
                    color: textColor
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                Text {
                    text: {
                        var size = data.size || data.data?.size || 0
                        if (size < 1024) return size + " B"
                        if (size < 1024 * 1024) return (size / 1024).toFixed(1) + " KB"
                        return (size / (1024 * 1024)).toFixed(1) + " MB"
                    }
                    color: "#cccccc"
                    font.pixelSize: 11
                }
            }
        }
    }
}
