import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Context (set before setSource): chromeMacActions, chromeTitleModel, chromeDragBridge

Item {
    id: root
    height: 36

    // 使用两个矩形拼接：顶部带圆角 + 底部平直
    // 顶部矩形只显示顶部圆角，通过负y值和足够高度来实现
    Rectangle {
        x: 0
        y: -10
        width: parent.width
        height: 20 + 10  // radius + extra
        color: "#3d3f4e"
        radius: 10
    }

    // 底部填充矩形，与content container背景色一致
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: parent.top
        anchors.topMargin: 15  // 稍微超过圆角起始位置确保无缝
        color: "#3d3f4e"
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
                    // backgroundColor会在MacWindowControls中根据dialogMode自动处理
                }
            }
        }

        Item { width: 8; height: 1 }

        Row {
            id: navRow
            visible: chromeTitleModel && chromeTitleModel.navVisible
            spacing: 4

            ToolButton {
                text: "◀"
                width: 24
                height: 24
                enabled: chromeTitleModel && chromeTitleModel.backEnabled
                flat: true
                background: Rectangle {
                    color: parent.hovered ? "#4c4f52" : "transparent"
                    radius: 4
                }
                contentItem: Label {
                    text: parent.text
                    color: parent.enabled ? "#888888" : "#444444"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 14
                    font.bold: true
                }
                onClicked: if (chromeTitleModel) chromeTitleModel.back()
            }
            ToolButton {
                text: "▶"
                width: 24
                height: 24
                enabled: chromeTitleModel && chromeTitleModel.forwardEnabled
                flat: true
                background: Rectangle {
                    color: parent.hovered ? "#4c4f52" : "transparent"
                    radius: 4
                }
                contentItem: Label {
                    text: parent.text
                    color: parent.enabled ? "#888888" : "#444444"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 14
                    font.bold: true
                }
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
