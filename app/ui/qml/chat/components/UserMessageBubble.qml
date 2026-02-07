// UserMessageBubble.qml - Right-aligned user message bubble
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string content: ""
    property bool isRead: true

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"

    implicitWidth: bubble.width
    implicitHeight: bubble.height

    // Right-aligned layout
    Row {
        anchors.right: parent.right
        spacing: 0
        layoutDirection: Qt.RightToLeft

        // Message bubble
        Rectangle {
            id: bubble
            width: Math.min(Math.max(80, contentText.implicitWidth + 24), root.width * 0.7)
            height: Math.min(contentText.implicitHeight + 24, 1000)

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
}
