// UserMessageBubble.qml - Right-aligned user message bubble with avatar
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

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

            // Calculate content width based on actual content
            property real calculatedContentWidth: 150

            width: Math.min(Math.max(80, calculatedContentWidth + bubblePadding * 2), availableWidth)
            height: contentLoader.height + bubblePadding * 2

            color: bubbleColor
            radius: 9

            // Structured content column
            Loader {
                id: contentLoader
                anchors {
                    left: parent.left
                    top: parent.top
                    margins: bubblePadding
                }
                width: availableWidth - bubblePadding * 2
                sourceComponent: structuredContentComponent

                onLoaded: {
                    // Use a timer to ensure all nested items are fully loaded
                    calcWidthTimer.start()
                }

                Timer {
                    id: calcWidthTimer
                    interval: 50
                    onTriggered: {
                        if (contentLoader.item && contentLoader.item.children) {
                            var maxW = 80
                            for (var i = 0; i < contentLoader.item.children.length; i++) {
                                var child = contentLoader.item.children[i]
                                // For Loaders, check their item's implicitWidth
                                if (child.item && child.item.implicitWidth !== undefined) {
                                    var w = child.item.implicitWidth
                                    if (w > maxW) maxW = w
                                }
                                // Also check the Loader's own implicitWidth
                                else if (child.implicitWidth !== undefined) {
                                    var w = child.implicitWidth
                                    if (w > maxW) maxW = w
                                }
                            }
                            bubble.calculatedContentWidth = maxW
                        }
                    }
                }
            }
        }
    }

    // Structured content component (renders widgets)
    Component {
        id: structuredContentComponent

        Column {
            id: contentColumn
            spacing: 8
            width: parent.width

            // Use a computed property that always has at least one item
            property var effectiveStructuredContent: {
                if (root.structuredContent && root.structuredContent.length > 0) {
                    return root.structuredContent
                }
                // Fallback: convert content to a simple text item
                return [{ content_type: "text", text: root.content || "" }]
            }

            Repeater {
                model: effectiveStructuredContent

                delegate: Loader {
                    id: widgetLoader
                    width: parent.width

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

        ImageWidget {
            property var data: ({})
            width: parent.width
            source: data.url || data.data?.url || ""
            caption: data.caption || data.data?.caption || ""
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

        FileWidget {
            property var data: ({})
            width: parent.width
            filePath: data.path || (data.data && data.data.path) ? data.data.path : ""
            fileName: data.name || (data.data && data.data.name) ? data.data.name : ""
            fileSize: data.size || (data.data && data.data.size) ? data.data.size : 0
        }
    }
}
