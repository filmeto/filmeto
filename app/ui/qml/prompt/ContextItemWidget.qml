import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // Matches Python ContextItemWidget API/semantics
    property string contextId: ""
    property string contextName: ""
    signal removeRequested(string contextId)

    // Python: contentsMargins(6,4,6,4), spacing 6, remove button 18x18
    // Height becomes ~18 + 4 + 4 = 26
    implicitHeight: 26
    implicitWidth: Math.max(60, nameText.implicitWidth + removeButton.implicitWidth + 6 + 6 + 6)

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 6
        color: hover.hovered ? "#4a4c5a" : "#3d3f4e"
        border.color: hover.hovered ? "#606264" : "#505254"
        border.width: 1
    }

    HoverHandler { id: hover }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        anchors.topMargin: 4
        anchors.bottomMargin: 4
        spacing: 6

        Text {
            id: nameText
            Layout.fillWidth: true
            text: root.contextName
            color: "#e1e1e1"
            font.pixelSize: 12
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
        }

        ToolButton {
            id: removeButton
            Layout.alignment: Qt.AlignVCenter
            width: 18
            height: 18
            padding: 0
            focusPolicy: Qt.NoFocus
            hoverEnabled: true
            text: "×"

            background: Rectangle {
                radius: 9
                color: removeButton.pressed ? "#6a6c7a"
                     : (removeButton.hovered ? "#5a5c6a" : "transparent")
            }

            contentItem: Text {
                text: removeButton.text
                color: removeButton.hovered ? "#ffffff" : "#a0a0a0"
                font.pixelSize: 14
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            onClicked: root.removeRequested(root.contextId)
        }
    }
}

