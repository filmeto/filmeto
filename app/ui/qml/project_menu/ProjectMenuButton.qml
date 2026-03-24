import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    width: 120
    height: 32
    radius: 4
    readonly property bool darkMode: bridge ? bridge.darkMode : true
    color: darkMode
           ? (ma.containsMouse ? "#4c5052" : "#3c3f41")
           : (ma.containsMouse ? "#ececec" : "#f5f5f5")
    border.color: darkMode ? "#555555" : "#cfcfcf"
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
            color: darkMode ? "#4d69ff" : "#3f63ff"

            Text {
                anchors.centerIn: parent
                text: bridge && bridge.projectName && bridge.projectName.length > 0 ? bridge.projectName.charAt(0).toUpperCase() : "P"
                color: "#ffffff"
                font.pixelSize: 12
                font.bold: true
            }
        }

        Text {
            Layout.fillWidth: true
            text: bridge ? bridge.projectName : ""
            color: darkMode ? "#ffffff" : "#222222"
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            font.pixelSize: 12
        }

        Text {
            text: "▼"
            color: darkMode ? "#d0d0d0" : "#666666"
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
