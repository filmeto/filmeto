import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Context (set before setSource): chromeMacActions, chromeTitleModel, chromeDragBridge

Item {
    id: root
    height: 36

    // Theme colors - match CustomDialog.qml theme
    readonly property color titleBarBackground: "#3d3f4e"
    readonly property color navButtonHover: "#4c4f52"
    readonly property color navButtonEnabled: "#888888"
    readonly property color navButtonDisabled: "#444444"
    readonly property color titleTextColor: "#E1E1E1"

    // Background with top rounded corners using clip approach
    Rectangle {
        anchors.fill: parent
        color: root.titleBarBackground
        // Top rounded corners only
        radius: 10
        // Clip bottom corners to be square
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: parent.radius
            color: parent.color
        }
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
                    color: parent.hovered ? root.navButtonHover : "transparent"
                    radius: 4
                }
                contentItem: Label {
                    text: parent.text
                    color: parent.enabled ? root.navButtonEnabled : root.navButtonDisabled
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
                    color: parent.hovered ? root.navButtonHover : "transparent"
                    radius: 4
                }
                contentItem: Label {
                    text: parent.text
                    color: parent.enabled ? root.navButtonEnabled : root.navButtonDisabled
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
                color: root.titleTextColor
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
