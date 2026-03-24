import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "transparent"
    width: 40
    property var bridge: startupRightBarBridge

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 20

        Repeater {
            model: bridge ? bridge.buttons : []
            delegate: ToolButton {
                required property var modelData
                Layout.alignment: Qt.AlignHCenter
                width: 30
                height: 30
                checkable: true
                checked: bridge && bridge.selectedPanel === modelData.panel
                text: modelData.icon
                font.family: "iconfont"
                ToolTip.visible: hovered
                ToolTip.text: modelData.tooltip
                onClicked: if (bridge) bridge.select_panel(modelData.panel)
            }
        }

        Item { Layout.fillHeight: true }
    }
}
