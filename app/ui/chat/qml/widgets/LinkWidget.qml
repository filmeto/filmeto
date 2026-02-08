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

    width: parent ? parent.width : 0
    height: linkColumn.implicitHeight + 20  // 2 * margins (10)
    implicitWidth: width
    implicitHeight: height

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

        // Link icon and URL
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "🔗"
                font.pixelSize: 14
            }

            Text {
                Layout.fillWidth: true
                text: root.url
                color: textColor
                font.pixelSize: 12
                font.family: "monospace"
                elide: Text.ElideMiddle
            }
        }

        // Optional title
        Text {
            visible: root.title !== ""
            Layout.fillWidth: true
            text: root.title
            color: titleColor
            font.pixelSize: 13
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
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
