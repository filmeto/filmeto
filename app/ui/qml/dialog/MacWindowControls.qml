import QtQuick 2.15

// macActions: MacWindowControlsViewModel, dialogMode: bool — set from Python root properties.
Item {
    id: root
    height: 36
    implicitWidth: row.width + 16

    property bool dialogMode: true
    property var macActions: null
    property color backgroundColor: "#3d3f4e"

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
    }

    MouseArea {
        id: hoverStrip
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    readonly property bool showGlyphs: hoverStrip.containsMouse || closeMa.containsMouse
                                       || minMa.containsMouse || greenMa.containsMouse

    Row {
        id: row
        spacing: 8
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 8

        Item {
            id: closeBtn
            width: 12
            height: 12
            Rectangle { anchors.fill: parent; radius: 6; color: "#ff5f56" }
            Canvas {
                anchors.fill: parent
                visible: root.showGlyphs
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#823c32"
                    ctx.lineWidth = 1.2
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.moveTo(4, 4)
                    ctx.lineTo(8, 8)
                    ctx.moveTo(8, 4)
                    ctx.lineTo(4, 8)
                    ctx.stroke()
                }
                onVisibleChanged: requestPaint()
            }
            MouseArea {
                id: closeMa
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (macActions) macActions.close_window()
            }
        }

        Item {
            id: minBtn
            width: 12
            height: 12
            Rectangle { anchors.fill: parent; radius: 6; color: "#ffbd2e" }
            Canvas {
                anchors.fill: parent
                visible: root.showGlyphs
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#823c32"
                    ctx.lineWidth = 1.2
                    ctx.beginPath()
                    ctx.moveTo(3, 6)
                    ctx.lineTo(9, 6)
                    ctx.stroke()
                }
                onVisibleChanged: requestPaint()
            }
            MouseArea {
                id: minMa
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (macActions) macActions.minimize_window()
            }
        }

        Item {
            id: greenBtn
            width: 12
            height: 12
            Rectangle { anchors.fill: parent; radius: 6; color: "#27c93f" }
            Canvas {
                anchors.fill: parent
                visible: root.showGlyphs
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = "#823c32"
                    ctx.lineWidth = 1.2
                    ctx.lineCap = "round"
                    var maxed = macActions ? macActions.windowMaximized : false
                    if (root.dialogMode) {
                        ctx.beginPath()
                        ctx.moveTo(3, 6)
                        ctx.lineTo(9, 6)
                        ctx.stroke()
                    } else if (maxed) {
                        ctx.beginPath()
                        ctx.moveTo(4, 5)
                        ctx.lineTo(4, 3)
                        ctx.lineTo(6, 3)
                        ctx.stroke()
                        ctx.beginPath()
                        ctx.moveTo(8, 7)
                        ctx.lineTo(8, 9)
                        ctx.lineTo(6, 9)
                        ctx.stroke()
                    } else {
                        ctx.beginPath()
                        ctx.moveTo(3, 3)
                        ctx.lineTo(3, 6)
                        ctx.lineTo(6, 3)
                        ctx.stroke()
                        ctx.beginPath()
                        ctx.moveTo(9, 9)
                        ctx.lineTo(9, 6)
                        ctx.lineTo(6, 9)
                        ctx.stroke()
                    }
                }
                onVisibleChanged: requestPaint()
                Connections {
                    target: macActions
                    function onMaximizedChanged() { parent.requestPaint() }
                }
            }
            MouseArea {
                id: greenMa
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (macActions) macActions.green_window()
            }
        }
    }
}
