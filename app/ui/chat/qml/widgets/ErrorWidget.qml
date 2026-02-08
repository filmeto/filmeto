// ErrorWidget.qml - Widget for displaying error messages
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property string errorMessage: ""
    property string errorType: ""
    property var errorDetails: ({})

    color: "#3a1a1a"
    radius: 6
    border.color: "#f44336"
    border.width: 1
    width: parent.width
    height: errorColumn.height + 16

    Column {
        id: errorColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        // Error header
        Row {
            spacing: 8
            width: parent.width

            Text {
                text: "⚠"
                font.pixelSize: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                id: errorTypeText
                text: root.errorType || "Error"
                color: "#f44336"
                font.pixelSize: 13
                font.weight: Font.Medium
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        // Error message
        Text {
            id: errorMessageText
            width: parent.width
            text: root.errorMessage
            color: "#e0e0e0"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Error details (collapsed by default)
        Rectangle {
            id: detailsRect
            width: parent.width
            height: detailsColumn.implicitHeight + 12
            color: "#2a1515"
            radius: 4
            visible: Object.keys(root.errorDetails || {}).length > 0 && showDetails.checked

            Column {
                id: detailsColumn
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 8
                }
                spacing: 4

                Text {
                    text: "Details:"
                    color: "#888888"
                    font.pixelSize: 11
                    font.weight: Font.Medium
                }

                Repeater {
                    model: Object.keys(root.errorDetails || {}).length

                    Row {
                        spacing: 8
                        width: parent.width

                        Text {
                            text: Object.keys(root.errorDetails)[index] + ":"
                            color: "#666666"
                            font.pixelSize: 11
                        }

                        Text {
                            text: String(Object.values(root.errorDetails)[index])
                            color: "#888888"
                            font.pixelSize: 11
                            width: parent.width - x - parent.spacing
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        // Show details toggle
        CheckBox {
            id: showDetails
            text: "Show details"
            visible: Object.keys(root.errorDetails || {}).length > 0
        }
    }
}
