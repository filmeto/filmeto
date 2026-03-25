import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    // Dimensions provided by Python (fallbacks keep it safe)
    property int leftPanelWidth: 250
    property int rightTitleBarHeight: 40
    property bool showRightTitleBar: true

    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: "transparent"
    }

    Rectangle {
        id: leftPanelBg
        x: 0
        y: 0
        width: root.leftPanelWidth
        height: parent.height
        color: "#2b2d30"
        border.color: "#505254"
        border.width: 1
    }

    Rectangle {
        id: rightBg
        x: root.leftPanelWidth
        y: 0
        width: parent.width - root.leftPanelWidth
        height: parent.height
        color: "#1e1f22"
        border.color: "#505254"
        border.width: 1
    }

    Rectangle {
        id: rightTitleBarBg
        visible: root.showRightTitleBar
        x: root.leftPanelWidth
        y: 0
        width: parent.width - root.leftPanelWidth
        height: root.rightTitleBarHeight
        color: "#2b2d30"
        border.color: "#505254"
        border.width: 1
    }
}

