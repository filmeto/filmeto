// LlmOutputWidget.qml - Collapsible LLM output display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string output: ""
    property string title: "LLM Output"
    property color widgetColor: "#9b59b6"
    property bool isCollapsible: true

    readonly property color bgColor: "#252525"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#a0a0a0"
    readonly property color titleColor: widgetColor

    color: bgColor
    radius: 6
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: column.implicitHeight + 12

    Layout.fillWidth: true

    property bool expanded: false  // Default collapsed

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

            // LLM icon
            Text {
                text: ""
                font.pixelSize: 14
                color: titleColor
            }

            // Title
            Text {
                text: root.title
                color: titleColor
                font.pixelSize: 12
                font.weight: Font.Medium
            }

            Item { Layout.fillWidth: true }

            // Output preview (first 50 chars when collapsed)
            Text {
                visible: false  // Hide preview when collapsed
                text: root.output.length > 50 ? root.output.substring(0, 50) + "..." : root.output
                color: textColor
                font.pixelSize: 11
                opacity: 0.7
                elide: Text.ElideRight
                Layout.maximumWidth: 200
            }

            // Collapse/expand indicator
            Text {
                text: root.expanded ? "" : ""
                color: textColor
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.expanded = !root.expanded
                }
            }
        }

        // Output content (collapsible)
        Loader {
            id: contentLoader
            Layout.fillWidth: true
            Layout.preferredHeight: active ? implicitHeight : 0
            visible: active
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
                    text: root.output
                    color: textColor
                    font.pixelSize: 12
                    font.family: "monospace"
                    wrapMode: Text.WordWrap
                    textFormat: Text.PlainText
                    lineHeight: 1.4
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
