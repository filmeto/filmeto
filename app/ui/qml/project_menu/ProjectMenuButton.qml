import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 120
    height: 32
    radius: 4
    color: ma.containsMouse ? "#4c5052" : "#3c3f41"
    border.color: "#555555"
    border.width: 1

    property var bridge: projectMenuBridge

    RowLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 6

        Rectangle {
            width: 20
            height: 20
            radius: 5
            color: "#4d69ff"

            Text {
                anchors.centerIn: parent
                text: bridge && bridge.projectName && bridge.projectName.length > 0 ? bridge.projectName.charAt(0).toUpperCase() : "P"
                color: "white"
                font.pixelSize: 12
                font.bold: true
            }
        }

        Text {
            Layout.fillWidth: true
            text: bridge ? bridge.projectName : ""
            color: "#ffffff"
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 12
        }

        Text {
            text: "▼"
            color: "#d0d0d0"
            font.pixelSize: 10
            verticalAlignment: Text.AlignVCenter
        }
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (bridge) bridge.open_menu()
    }
}
