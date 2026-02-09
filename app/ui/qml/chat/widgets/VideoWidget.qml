// VideoWidget.qml - Video content display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property url source: ""
    property string caption: ""
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: videoColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: videoColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 12

        // Video placeholder with play button
        Rectangle {
            width: parent.width
            height: Math.min(200, width * 9 / 16)  // 16:9 aspect ratio, max height 200
            color: "#1a1a1a"
            radius: 4

            // Play icon overlay
            Column {
                anchors.centerIn: parent
                spacing: 8

                Text {
                    text: "🎬"
                    font.pixelSize: 48
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: "Video"
                    color: "#808080"
                    font.pixelSize: 12
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: root.source.toString().substring(0, 40) + (root.source.toString().length > 40 ? "..." : "")
                    color: "#606060"
                    font.pixelSize: 10
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }

            // Clickable area
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (root.source > "") {
                        Qt.openUrlExternally(root.source)
                    }
                }
                cursorShape: Qt.PointingHandCursor
            }
        }

        // Caption text
        Text {
            id: captionText
            visible: root.caption > ""
            width: parent.width
            text: root.caption
            color: "#d0d0d0"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
        }
    }
}
