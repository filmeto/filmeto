// ImageWidget.qml - Display images with captions
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root

    property string source: ""
    property string caption: ""

    spacing: 8
    Layout.fillWidth: true

    // Image container
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(image.sourceSize.height * (width / image.sourceSize.width), 400)
        Layout.maximumHeight: 400

        color: "#1e1e1e"
        radius: 8

        border.color: "#404040"
        border.width: 1

        // Image with loading state
        Image {
            id: image
            anchors {
                fill: parent
                margins: 4
            }
            source: root.source
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true

            // Loading indicator
            BusyIndicator {
                anchors.centerIn: parent
                running: image.status === Image.Loading
            }

            // Error indicator
            Text {
                anchors.centerIn: parent
                text: "⚠️ Failed to load image"
                color: "#ff6b6b"
                visible: image.status === Image.Error
            }

            // Click to view full size
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    // Open image in external viewer
                    Qt.openUrlExternally(root.source)
                }
            }

            // Hover effect
            Rectangle {
                anchors.fill: parent
                color: "#ffffff"
                opacity: parentMouse.containsMouse ? 0.1 : 0.0
                radius: parent.radius

                MouseArea {
                    id: parentMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }
            }

            Behavior on opacity {
                NumberAnimation { duration: 100 }
            }
        }
    }

    // Optional caption
    Text {
        visible: root.caption !== ""
        Layout.fillWidth: true
        text: root.caption
        color: "#a0a0a0"
        font.pixelSize: 12
        font.italic: true
        wrapMode: Text.WordWrap
    }
}
