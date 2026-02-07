// UserMessageBubble.qml - Right-aligned user message bubble
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string content: ""
    property bool isRead: true

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"

    // Don't set implicitWidth - let the bubble determine it
    implicitHeight: bubble.height

    // Message bubble positioned on the right
    Rectangle {
        id: bubble
        anchors {
            right: parent.right
            top: parent.top
        }
        width: Math.min(Math.max(80, contentText.implicitWidth + 24), 500)
        height: contentText.implicitHeight + 24

        color: bubbleColor
        radius: 18

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
