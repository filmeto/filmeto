import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/* Matches edit window MainWindowRightSideBar: QPushButton global + checkable (#005a9e when checked) */
Rectangle {
    id: root
    color: "#2b2d30"
    width: 40

    signal panelSelected(string panelName)

    property string selectedPanel: "members"
    property var buttons: ([
        {"panel": "project_info", "icon": "\ue60f", "tooltip": "Project"},
        {"panel": "members", "icon": "\ue89e", "tooltip": "Members"},
        {"panel": "screenplay", "icon": "\ue993", "tooltip": "Screen Play"},
        {"panel": "plan", "icon": "\ue8a5", "tooltip": "Plan Management"}
    ])

    function selectPanel(panelName, emitSignal) {
        var p = panelName || "members"
        root.selectedPanel = p
        if (emitSignal === true) {
            root.panelSelected(p)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 20

        Repeater {
            model: root.buttons
            delegate: ToolButton {
                id: btn
                required property var modelData
                Layout.alignment: Qt.AlignHCenter
                width: 30
                height: 30
                checkable: true
                checked: root.selectedPanel === modelData.panel
                text: modelData.icon
                font.family: "iconfont"
                font.pixelSize: 20
                flat: true
                hoverEnabled: true
                ToolTip.visible: btn.hovered
                ToolTip.text: modelData.tooltip
                onClicked: root.selectPanel(modelData.panel, true)

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
