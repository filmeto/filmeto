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
            rightMargin: 40  // avatar (32) + spacing (8)
            top: headerRow.bottom
            topMargin: 12
        }
        width: bubble.width
        height: bubble.height

        // Message bubble
        Rectangle {
            id: bubble
            width: Math.min(Math.max(80, contentText.implicitWidth + 24), availableWidth)
            height: contentText.implicitHeight + 24

            color: bubbleColor
            radius: 9

            // Content
            Text {
                id: contentText
                anchors {
                    fill: parent
                    margins: 12
                }

                text: root.content
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
}
