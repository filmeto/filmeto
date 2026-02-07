// ThinkingWidget.qml - Collapsible thinking process display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string thought: ""
    property string title: "Thinking Process"
    property color widgetColor: "#4a90e2"
    property bool isCollapsible: true

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#b0b0b0"
    readonly property color titleColor: widgetColor

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: column.implicitHeight + 12

    Layout.fillWidth: true

    property bool expanded: false

    ColumnLayout {
        id: column
        anchors {
            fill: parent
            margins: 8
        }
        spacing: 8

        // Header with title and toggle
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Thinking icon
            Text {
                text: "🤔"
                font.pixelSize: 16
            }

            // Title
            Text {
                text: root.title
                color: titleColor
                font.pixelSize: 13
                font.weight: Font.Medium
            }

            Item { Layout.fillWidth: true }

            // Collapse/expand indicator
            Text {
                text: root.expanded ? "▼" : "▶"
                color: textColor
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.expanded = !root.expanded
                }
            }
        }

        // Thought content (collapsible)
        Loader {
            id: contentLoader
            Layout.fillWidth: true
            active: root.expanded || !root.isCollapsible
            sourceComponent: ColumnLayout {
                spacing: 4

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: borderColor
                }

                Text {
                    Layout.fillWidth: true
                    text: root.thought
                    color: textColor
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    lineHeight: 1.5
                }
            }
        }
    }

    // Click on header to toggle
    MouseArea {
        anchors.fill: parent
        propagateComposedEvents: true
        onPressed: function(mouse) {
            // Only toggle if clicking on the header area
            if (mouse.y < 40 && root.isCollapsible) {
                root.expanded = !root.expanded
            }
            mouse.accepted = false
        }
    }

    // Smooth expand/collapse animation
    Behavior on implicitHeight {
        NumberAnimation {
            duration: 200
            easing.type: Easing.InOutQuad
        }
    }
}
