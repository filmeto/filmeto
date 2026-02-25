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
    property string startTime: ""     // Formatted start time
    property string duration: ""      // Formatted duration (e.g., "2m 30s")

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"
    readonly property color avatarColor: "#6fa8e8"
    readonly property color timeInfoColor: "#707070"
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Internal bubble padding
    readonly property int bubblePadding: 12

    // Available width for bubble (total width minus avatar space on both sides)
    readonly property int availableWidth: Math.max(80, width - totalAvatarWidth)

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: 12 + headerRow.height + 12 + bubbleContainer.height + 8

    // Header row - right aligned with time info, name, and avatar
    Row {
        id: headerRow
        anchors {
            right: parent.right
            rightMargin: 12
            top: parent.top
            topMargin: 12
        }
        spacing: 8
        height: Math.max(avatarRect.height, nameText.implicitHeight, timeInfoColumn.implicitHeight)

        // Time info column (before name)
        Column {
            id: timeInfoColumn
            spacing: 0
            anchors.verticalCenter: parent.verticalCenter
            visible: root.startTime !== "" || root.duration !== ""

            Text {
                text: root.startTime
                color: timeInfoColor
                font.pixelSize: 11
                font.weight: Font.Light
                visible: root.startTime !== ""
            }

            Text {
                text: root.duration
                color: timeInfoColor
                font.pixelSize: 10
                font.weight: Font.Light
                visible: root.duration !== ""
            }
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
            height: contentLoader.implicitHeight + bubblePadding * 2

            color: bubbleColor
            radius: 9

            // Structured content column - render through structured content
            StructuredContentRenderer {
                id: contentLoader
                anchors {
                    left: parent.left
                    top: parent.top
                    margins: bubblePadding
                }
                width: availableWidth - bubblePadding * 2
                structuredContent: root.structuredContent
                content: root.content
                textColor: root.textColor
                widgetColor: root.bubbleColor
                widgetSupport: "basic"
                onReferenceClicked: function(refType, refId) {
                    root.referenceClicked(refType, refId)
                }

                onImplicitHeightChanged: {
                    // Trigger bubble width recalculation when content changes
                    // Use restart() to debounce rapid height changes during content updates
                    calcWidthTimer.restart()
                }

                Timer {
                    id: calcWidthTimer
                    interval: 100  // Increased from 50ms to reduce frequency during rapid updates
                    onTriggered: {
                        if (contentLoader.children && contentLoader.children.length > 0) {
                            var maxW = 80
                            // contentLoader.children[0] is the contentColumn
                            var contentColumn = contentLoader.children[0]
                            if (contentColumn && contentColumn.children) {
                                for (var i = 0; i < contentColumn.children.length; i++) {
                                    var child = contentColumn.children[i]
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
                            }
                            bubble.calculatedContentWidth = maxW
                        }
                    }
                }
            }
        }
    }
}
