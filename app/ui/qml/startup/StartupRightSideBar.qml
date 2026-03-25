import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/* Matches edit window MainWindowRightSideBar: QPushButton global + checkable (#005a9e when checked) */
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
                id: btn
                required property var modelData
                Layout.alignment: Qt.AlignHCenter
                width: 30
                height: 30
                checkable: true
                checked: bridge && bridge.selectedPanel === modelData.panel
                text: modelData.icon
                font.family: "iconfont"
                font.pixelSize: 20
                flat: true
                hoverEnabled: true
                ToolTip.visible: btn.hovered
                ToolTip.text: modelData.tooltip
                onClicked: if (bridge) bridge.select_panel(modelData.panel)

                background: Rectangle {
                    radius: 5
                    color: btn.pressed ? "#005a9e" : (btn.checked ? "#005a9e" : (btn.hovered ? "#616161" : "transparent"))
                }
                contentItem: Text {
                    text: btn.text
                    font: btn.font
                    color: btn.checked ? "#FFFFFF" : "#C0C0C0"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
