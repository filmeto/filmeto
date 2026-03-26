import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common/buttons" as CommonButtons

// Context (set before setSource): chromeMacActions, chromeTitleModel, chromeDragBridge

Item {
    id: root
    height: 36

    Rectangle {
        anchors.fill: parent
        color: "#3d3f4e"
        radius: 10
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Loader {
            id: macLoader
            source: "MacWindowControls.qml"
            width: item ? item.implicitWidth : 68
            height: 36
            onLoaded: {
                if (item) {
                    item.macActions = chromeMacActions
                    item.dialogMode = true
                    item.backgroundColor = "transparent"
                }
            }
        }

        Item { width: 8; height: 1 }

        Row {
            id: navRow
            visible: chromeTitleModel && chromeTitleModel.navVisible
            spacing: 4

            CommonButtons.IconButton {
                iconCode: "◀"
                size: "small"
                enabled: chromeTitleModel && chromeTitleModel.backEnabled
                iconColor: enabled ? "#888888" : "#444444"
                onClicked: if (chromeTitleModel) chromeTitleModel.back()
            }
            CommonButtons.IconButton {
                iconCode: "▶"
                size: "small"
                enabled: chromeTitleModel && chromeTitleModel.forwardEnabled
                iconColor: enabled ? "#888888" : "#444444"
                onClicked: if (chromeTitleModel) chromeTitleModel.forward()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Label {
                id: titleLabel
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 4
                text: chromeTitleModel ? chromeTitleModel.title : ""
                color: "#E1E1E1"
                font.pixelSize: 14
                font.bold: true
                elide: Text.ElideRight
                width: parent.width - 8
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.ArrowCursor
                onPressed: function (m) {
                    var g = mapToGlobal(Qt.point(m.x, m.y))
                    if (chromeDragBridge)
                        chromeDragBridge.drag_begin(g.x, g.y)
                }
                onPositionChanged: function (m) {
                    if (pressed && chromeDragBridge) {
                        var g = mapToGlobal(Qt.point(m.x, m.y))
                        chromeDragBridge.drag_move(g.x, g.y)
                    }
                }
                onReleased: if (chromeDragBridge) chromeDragBridge.drag_end()
            }
        }
    }
}
