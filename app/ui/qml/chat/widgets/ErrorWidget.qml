// ErrorWidget.qml - Error message display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var errorData: {}  // {error_message, error_type, details}
    property color widgetColor: "#ff6b6b"  // Error color

    implicitWidth: parent.width
    implicitHeight: errorColumn.implicitHeight + 24

    color: "#2a1a1a"  // Slightly reddish background for errors
    radius: 6
    border.color: Qt.rgba(1, 0.4, 0.4, 0.4)
    border.width: 1

    Column {
        id: errorColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 8

        // Header row with icon and title
        Row {
            width: parent.width
            spacing: 8

            // Error icon
            Text {
                text: "❌"
                font.pixelSize: 18
                anchors.verticalCenter: parent.verticalCenter
            }

            // Error type/title
            Text {
                width: parent.width - 26
                text: root.errorData.error_type || "Error"
                color: root.widgetColor
                font.pixelSize: 13
                font.weight: Font.Bold
                wrapMode: Text.WordWrap
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Error message
        Text {
            width: parent.width
            text: root.errorData.error_message || ""
            color: "#e0e0e0"
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
        }

        // Details section (collapsible)
        Column {
            visible: root.errorData.details > ""
            width: parent.width
            spacing: 4

            // Separator line
            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            // Details label
            Text {
                text: "Details:"
                color: "#808080"
                font.pixelSize: 11
                font.weight: Font.Medium
            }

            // Details text
            Text {
                width: parent.width
                text: root.errorData.details || ""
                color: "#a0a0a0"
                font.pixelSize: 11
                font.family: "monospace"
                wrapMode: Text.WordWrap
                textFormat: Text.PlainText
            }
        }

        // Stack trace (if available)
        Column {
            visible: root.errorData.stack_trace > ""
            width: parent.width
            spacing: 4

            Rectangle {
                width: parent.width
                height: 1
                color: "#404040"
            }

            Text {
                text: "Stack trace:"
                color: "#808080"
                font.pixelSize: 11
                font.weight: Font.Medium
            }

            Rectangle {
                width: parent.width
                height: stackTraceText.implicitHeight + 16
                color: "#1a1a1a"
                radius: 4

                Flickable {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    width: parent.width
                    height: parent.height
                    clip: true
                    contentHeight: stackTraceText.implicitHeight

                    Text {
                        id: stackTraceText
                        width: parent.width
                        text: root.errorData.stack_trace || ""
                        color: "#ff6b6b"
                        font.pixelSize: 10
                        font.family: "monospace"
                        wrapMode: Text.WordWrap
                        textFormat: Text.PlainText
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                }
            }
        }
    }
}
