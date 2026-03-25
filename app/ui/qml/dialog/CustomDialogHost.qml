import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property int radius: 10
    property color backgroundColor: "#2b2d30"
    property color borderColor: "#505254"
    property int borderWidth: 1

    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.backgroundColor
        border.color: root.borderColor
        border.width: root.borderWidth
    }
}

