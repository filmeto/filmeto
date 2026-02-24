// MetadataWidget.qml - Metadata/system event display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var metadataData: ({})  // {metadata_type, metadata_data, title, description}
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: metadataColumn.implicitHeight + 20

    color: "#252525"  // Slightly darker than normal content
    radius: 4
    border.color: "#404040"
    border.width: 1

    // Dashed border effect using border
    Rectangle {
        anchors {
            fill: parent
            margins: 2
        }
        color: "transparent"
        radius: parent.radius - 1
        border.color: "#505050"
        border.width: 1
    }

    Column {
        id: metadataColumn
        anchors {
            fill: parent
            margins: 10
        }
        spacing: 6

        // Title row with icon
        Row {
            visible: root.metadataData.title > ""
            width: parent.width
            spacing: 6

            Text {
                text: "ℹ"
                color: "#808080"
                font.pixelSize: 11
                anchors.verticalCenter: parent.verticalCenter
            }

            SelectableText {
                width: parent.width - 26
                text: root.metadataData.title || ""
                textColor: "#808080"
                fontPixelSize: 11
                wrapMode: true
                selectionColor: root.widgetColor
            }
        }

        // Description with selection support
        SelectableText {
            visible: root.metadataData.description > ""
            width: parent.width
            text: root.metadataData.description || ""
            textColor: "#707070"
            fontPixelSize: 10
            wrapMode: true
            selectionColor: root.widgetColor
        }

        // Key-value pairs display with selection support
        Column {
            visible: Object.keys(root.metadataData.metadata_data || {}).length > 0
            width: parent.width
            spacing: 2

            Repeater {
                model: Object.keys(root.metadataData.metadata_data || {})

                Row {
                    width: parent.width
                    spacing: 4

                    SelectableText {
                        width: parent.width * 0.4
                        text: modelData + ":"
                        textColor: "#707070"
                        fontPixelSize: 10
                        wrapMode: true
                        selectionColor: root.widgetColor
                    }

                    SelectableText {
                        width: parent.width * 0.6
                        text: formatValue(root.metadataData.metadata_data[modelData])
                        textColor: "#606060"
                        fontPixelSize: 10
                        wrapMode: true
                        selectionColor: root.widgetColor
                    }
                }
            }
        }
    }

    // Format value for display
    function formatValue(value) {
        if (typeof value === "object") {
            return JSON.stringify(value)
        }
        return String(value)
    }
}
