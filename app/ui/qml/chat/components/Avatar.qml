import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string icon: "👤"
    property color color: "#4a90e2"
    property int size: 32
    property string shape: "circle" // "circle" | "rounded_rect"
    property color textColor: "#ffffff"

    width: size
    height: size

    Rectangle {
        id: bg
        anchors.fill: parent
        color: root.color
        radius: root.shape === "circle" ? width / 2 : Math.max(2, Math.floor(width / 4))
        antialiasing: true

        Text {
            anchors.centerIn: parent
            text: root.icon
            color: root.textColor
            font.bold: true
            font.pixelSize: Math.max(10, Math.floor(root.size / 2))
        }
    }
}

