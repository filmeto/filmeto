// LinkWidget.qml - Clickable link with preview
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string url: ""
    property string title: ""

    readonly property color bgColor: "#2a2a2a"
    readonly property color bgColorHover: "#353535"
    readonly property color borderColor: "#404040"
    readonly property color textColor: "#4a90e2"
    readonly property color titleColor: "#e0e0e0"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: linkColumn.implicitHeight + 16

    Layout.fillWidth: true

    // Hover state
    property bool isHovered: false

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.isHovered = true
        onExited: root.isHovered = false
        onClicked: Qt.openUrlExternally(root.url)
    }

    ColumnLayout {
        id: linkColumn
        anchors {
            fill: parent
            margins: 10
        }
        spacing: 4

        // Link icon and URL with selection support
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "🔗"
                font.pixelSize: 14
            }

            SelectableText {
                Layout.fillWidth: true
                text: root.url
                textColor: textColor
                fontPixelSize: 12
                wrapMode: false
                selectionColor: root.textColor
            }
        }

        // Optional title with selection support
        SelectableText {
            visible: root.title !== ""
            Layout.fillWidth: true
            text: root.title
            textColor: titleColor
            fontPixelSize: 13
            wrapMode: true
            selectionColor: root.textColor
        }
    }

    // Hover effect
    Behavior on color {
        ColorAnimation {
            duration: 150
            to: isHovered ? bgColorHover : bgColor
        }
    }
}
