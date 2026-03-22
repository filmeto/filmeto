// Section.qml - A section/group container for configuration fields

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Rectangle {
    id: root

    property string title: ""
    property bool collapsible: false
    property bool collapsed: false

    default property alias content: contentContainer.children

    color: Theme.cardBackground
    radius: 4
    border.color: Theme.border
    border.width: 1

    implicitHeight: layout.implicitHeight + 20

    ColumnLayout {
        id: layout
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Label {
                text: root.title
                font.bold: true
                font.pixelSize: 13
                color: Theme.textPrimary
                Layout.fillWidth: true
            }

            // Collapse toggle button (only visible if collapsible)
            ToolButton {
                visible: root.collapsible
                text: root.collapsed ? "\u25B6" : "\u25BC"  // Play or Down arrow
                font.pixelSize: 10
                onClicked: root.collapsed = !root.collapsed
                background: null
                contentItem: Text {
                    text: parent.text
                    color: Theme.textSecondary
                    font: parent.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Content container
        ColumnLayout {
            id: contentContainer
            Layout.fillWidth: true
            visible: !root.collapsed
            spacing: 10
        }
    }

    // Mouse area for collapsing (if collapsible)
    MouseArea {
        anchors.fill: parent
        enabled: root.collapsible
        onClicked: root.collapsed = !root.collapsed
        propagateComposedEvents: true

        onPressed: mouse.accepted = false
        onReleased: mouse.accepted = false
        onDoubleClicked: mouse.accepted = false
    }
}