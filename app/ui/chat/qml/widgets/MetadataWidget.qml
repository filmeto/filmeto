// MetadataWidget.qml - Widget for displaying metadata information
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property var metadata: ({})
    property string title: "Metadata"

    color: "#1a1a1a"
    radius: 4
    width: parent.width
    height: metadataColumn.height + 12

    Column {
        id: metadataColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 10
        }
        spacing: 6

        // Title
        Text {
            id: titleText
            text: root.title
            color: "#666666"
            font.pixelSize: 10
            font.weight: Font.Medium
            visible: root.title !== ""
        }

        // Metadata entries
        Repeater {
            model: Object.keys(root.metadata || {}).length

            Row {
                spacing: 8
                width: parent.width

                Text {
                    text: Object.keys(root.metadata)[index] + ":"
                    color: "#555555"
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: {
                        var value = Object.values(root.metadata)[index]
                        if (typeof value === "object") return JSON.stringify(value)
                        return String(value)
                    }
                    color: "#666666"
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - x - parent.spacing
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
