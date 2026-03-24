import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Context property: panelToolbarViewModel
Item {
    id: root
    implicitHeight: 40

    Rectangle {
        anchors.fill: parent
        color: "#2D2D2D"
        border.color: "#1E1E1E"
        border.width: 1
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 4

        Label {
            text: panelToolbarViewModel ? panelToolbarViewModel.title : ""
            color: "#E0E0E0"
            font.bold: true
            font.pixelSize: 12
            Layout.alignment: Qt.AlignVCenter
        }

        Item { Layout.fillWidth: true }

        Repeater {
            model: panelToolbarViewModel ? panelToolbarViewModel.actions : []
            delegate: Item {
                visible: modelData.visible
                width: visible ? 28 : 0
                height: 28

                Rectangle {
                    anchors.fill: parent
                    radius: 4
                    color: actionArea.pressed ? "#4D4D4D" : (actionArea.containsMouse ? "#3D3D3D" : "transparent")
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData.iconText
                    color: modelData.enabled ? "#A0A0A0" : "#666666"
                    font.family: "iconfont"
                    font.pixelSize: 16
                }

                MouseArea {
                    id: actionArea
                    anchors.fill: parent
                    hoverEnabled: true
                    enabled: modelData.enabled
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        if (panelToolbarViewModel) {
                            panelToolbarViewModel.invoke_action(modelData.id)
                        }
                    }
                }

                ToolTip.visible: actionArea.containsMouse && modelData.tooltip && modelData.tooltip.length > 0
                ToolTip.text: modelData.tooltip
            }
        }
    }
}
