// AudioWidget.qml - Audio content display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property url source: ""
    property string caption: ""
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: audioColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: audioColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 12

        // Audio placeholder with play button
        Rectangle {
            width: parent.width
            height: 60
            color: "#1a1a1a"
            radius: 4

            Row {
                anchors {
                    fill: parent
                    margins: 12
                }
                spacing: 12

                // Play button
                Rectangle {
                    width: 40
                    height: 40
                    radius: width / 2
                    color: root.widgetColor
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "▶"
                        font.pixelSize: 16
                        color: "#ffffff"
                    }

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

                // Audio info
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 40 - parent.spacing
                    spacing: 4

                    Text {
                        width: parent.width
                        text: "Audio File"
                        color: "#e0e0e0"
                        font.pixelSize: 13
                        font.weight: Font.Medium
                        elide: Text.ElideRight
                    }

                    Text {
                        width: parent.width
                        text: root.source.toString().substring(0, 50) + (root.source.toString().length > 50 ? "..." : "")
                        color: "#808080"
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                }
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
