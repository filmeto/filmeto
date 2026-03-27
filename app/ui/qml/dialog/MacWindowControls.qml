import QtQuick 2.15

// macActions: MacWindowControlsViewModel, dialogMode: bool — set from Python root properties.
Item {
    id: root
    height: 36
    implicitWidth: row.width + 16

    property bool dialogMode: false
    property var macActions: null

    // macOS traffic light colors - these are fixed design constants
    readonly property color closeColor: "#ff5f56"
    readonly property color minimizeColor: "#ffbd2e"
    readonly property color maximizeColor: "#27c93f"
    readonly property color closeGlyph: "#8e3a36"      // dark red for close symbol
    readonly property color minimizeGlyph: "#9a6a1b"   // dark yellow/orange for minimize symbol
    readonly property color maximizeGlyph: "#1a6d1e"   // dark green for maximize symbol

    // Background color - defaults to a common dark sidebar color
    property color backgroundColor: "#3d3f4e"

    // Background rectangle
    // In dialog mode, we still need background because the window has WA_TranslucentBackground
    // and QQuickWidget is transparent. The background color should match the parent panel.
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

        // Close button (red)
        Item {
            id: closeBtn
            width: 12
            height: 12
            Rectangle {
                anchors.fill: parent
                radius: 6
                color: root.closeColor
            }
            Canvas {
                id: closeCanvas
                anchors.fill: parent
                visible: root.showGlyphs
                // Cache the painted content to avoid redundant repaints
                renderTarget: Canvas.FramebufferObject
                onVisibleChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = root.closeGlyph
                    ctx.lineWidth = 1.2
                    ctx.lineCap = "round"
                    ctx.beginPath()
                    ctx.moveTo(4, 4)
                    ctx.lineTo(8, 8)
                    ctx.moveTo(8, 4)
                    ctx.lineTo(4, 8)
                    ctx.stroke()
                }
            }
            MouseArea {
                id: closeMa
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (macActions) macActions.close_window()
            }
        }

        // Minimize button (yellow)
        Item {
            id: minBtn
            width: 12
            height: 12
            Rectangle {
                anchors.fill: parent
                radius: 6
                color: root.minimizeColor
            }
            Canvas {
                id: minCanvas
                anchors.fill: parent
                visible: root.showGlyphs
                renderTarget: Canvas.FramebufferObject
                onVisibleChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = root.minimizeGlyph
                    ctx.lineWidth = 1.2
                    ctx.beginPath()
                    ctx.moveTo(3, 6)
                    ctx.lineTo(9, 6)
                    ctx.stroke()
                }
            }
            MouseArea {
                id: minMa
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: if (macActions) macActions.minimize_window()
            }
        }

        // Maximize/Zoom button (green)
        Item {
            id: greenBtn
            width: 12
            height: 12
            Rectangle {
                anchors.fill: parent
                radius: 6
                color: root.maximizeColor
            }
            Canvas {
                id: greenCanvas
                anchors.fill: parent
                visible: root.showGlyphs
                renderTarget: Canvas.FramebufferObject
                property bool isMaximized: macActions ? macActions.windowMaximized : false
                onIsMaximizedChanged: requestPaint()
                onVisibleChanged: requestPaint()
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = root.maximizeGlyph
                    ctx.lineWidth = 1.2
                    ctx.lineCap = "round"

                    if (root.dialogMode) {
                        // Dialog模式: 显示横线表示禁用
                        ctx.beginPath()
                        ctx.moveTo(3, 6)
                        ctx.lineTo(9, 6)
                        ctx.stroke()
                    } else if (isMaximized) {
                        // 最大化状态: 显示两个重叠的三角形
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
                        // 正常状态: 显示两个三角形
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
                Connections {
                    target: macActions
                    function onMaximizedChanged() { greenCanvas.requestPaint() }
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
