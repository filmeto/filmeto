import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    anchors.fill: parent
    color: "#1e1e1e"

    function ensureSelectedShotVisible() {
        if (!storyBoardViewModel || !storyBoardViewModel.selectedShotId || !scrollView.visible)
            return
        var flick = scrollView.contentItem
        if (!flick)
            return
        var target = null
        for (var i = 0; i < grid.children.length; ++i) {
            var child = grid.children[i]
            if (child && child.shotId !== undefined && child.shotId === storyBoardViewModel.selectedShotId) {
                target = child
                break
            }
        }
        if (!target)
            return

        var viewportHeight = flick.height > 0 ? flick.height : scrollView.availableHeight
        if (viewportHeight <= 0)
            return
        var padding = 12
        var targetTop = target.y
        var targetBottom = targetTop + target.height
        var viewTop = flick.contentY
        var viewBottom = viewTop + viewportHeight

        if (targetTop - padding < viewTop) {
            flick.contentY = Math.max(0, targetTop - padding)
            return
        }
        if (targetBottom + padding > viewBottom) {
            var desired = targetBottom + padding - viewportHeight
            var maxY = Math.max(0, flick.contentHeight - viewportHeight)
            flick.contentY = Math.min(maxY, desired)
        }
    }

    Connections {
        target: storyBoardViewModel
        function onSelectedShotIdChanged() {
            Qt.callLater(root.ensureSelectedShotVisible)
        }
        function onShotsReloaded() {
            Qt.callLater(root.ensureSelectedShotVisible)
        }
    }

    component IconToolButton: ToolButton {
        id: iconButton
        implicitWidth: 32
        implicitHeight: 32
        width: 32
        height: 32
        font.family: "iconfont"
        font.pixelSize: 18
        padding: 0
        background: Rectangle {
            radius: 4
            color: iconButton.down ? "#4D4D4D" : (iconButton.hovered ? "#3D3D3D" : "transparent")
        }
        contentItem: Text {
            text: iconButton.text
            font.family: iconButton.font.family
            font.pixelSize: iconButton.font.pixelSize
            color: iconButton.hovered ? "#FFFFFF" : "#A0A0A0"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            Layout.topMargin: 8
            Layout.bottomMargin: 8
            spacing: 8

            Label {
                text: typeof sbShotsSectionTitle !== "undefined" ? sbShotsSectionTitle : "Shots"
                color: "#d0d0d0"
                font.pixelSize: 13
                font.bold: true
            }

            IconToolButton {
                text: "\ue6b8"
                onClicked: if (storyBoardViewModel) storyBoardViewModel.on_refresh_clicked()
                ToolTip.visible: hovered
                ToolTip.text: "Refresh"
            }

            Button {
                id: addShotButton
                text: qsTr("Add shot")
                enabled: storyBoardViewModel && storyBoardViewModel.sceneLabels.length > 0
                implicitHeight: 30
                Layout.minimumWidth: 96
                onClicked: if (storyBoardViewModel) storyBoardViewModel.on_add_shot_clicked()
                ToolTip.visible: hovered
                ToolTip.text: qsTr("Create a new shot in the current scene")
                background: Rectangle {
                    implicitHeight: 30
                    implicitWidth: addShotButton.implicitWidth
                    radius: 4
                    color: !addShotButton.enabled ? "#3a3a3a"
                        : (addShotButton.down ? "#2d5aa8" : (addShotButton.hovered ? "#3d6ec4" : "#4080ff"))
                    border.width: 1
                    border.color: addShotButton.enabled ? "#5a8fff" : "#555555"
                }
                contentItem: Text {
                    text: addShotButton.text
                    font.pixelSize: 12
                    color: addShotButton.enabled ? "#ffffff" : "#888888"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Label {
                text: "Scene"
                color: "#b0b0b0"
                font.pixelSize: 12
            }

            ComboBox {
                id: sceneCombo
                Layout.fillWidth: false
                Layout.minimumWidth: 110
                Layout.maximumWidth: 260
                implicitWidth: Math.min(
                    Layout.maximumWidth,
                    Math.max(Layout.minimumWidth, contentItem.implicitWidth + 38)
                )
                implicitHeight: 30
                visible: storyBoardViewModel && storyBoardViewModel.sceneLabels.length > 0
                model: storyBoardViewModel ? storyBoardViewModel.sceneLabels : []
                currentIndex: storyBoardViewModel ? storyBoardViewModel.currentSceneIndex : 0
                leftPadding: 10
                rightPadding: 26
                font.pixelSize: 12

                delegate: ItemDelegate {
                    width: sceneCombo.width
                    highlighted: sceneCombo.highlightedIndex === index
                    contentItem: Text {
                        text: modelData
                        color: "#d8d8d8"
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.highlighted ? "#3b3d44" : "#2a2b2f"
                    }
                }

                indicator: Canvas {
                    x: sceneCombo.width - width - 10
                    y: (sceneCombo.height - height) / 2
                    width: 10
                    height: 6
                    contextType: "2d"
                    onPaint: {
                        context.reset()
                        context.moveTo(0, 0)
                        context.lineTo(width, 0)
                        context.lineTo(width / 2, height)
                        context.closePath()
                        context.fillStyle = "#bdbdbd"
                        context.fill()
                    }
                }

                contentItem: Text {
                    text: sceneCombo.displayText
                    color: "#e2e2e2"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: sceneCombo.leftPadding
                    rightPadding: sceneCombo.rightPadding
                }

                background: Rectangle {
                    radius: 4
                    color: "#2a2b2f"
                    border.width: 1
                    border.color: sceneCombo.activeFocus ? "#5a8fff" : "#4a4d57"
                }

                popup: Popup {
                    y: sceneCombo.height + 2
                    width: sceneCombo.width
                    padding: 1
                    contentItem: ListView {
                        clip: true
                        implicitHeight: contentHeight
                        model: sceneCombo.popup.visible ? sceneCombo.delegateModel : null
                        currentIndex: sceneCombo.highlightedIndex
                    }
                    background: Rectangle {
                        radius: 4
                        color: "#2a2b2f"
                        border.width: 1
                        border.color: "#4a4d57"
                    }
                }
                onActivated: function (i) {
                    if (storyBoardViewModel)
                        storyBoardViewModel.set_current_scene_index(i)
                }
            }

            Item {
                Layout.fillWidth: true
            }
        }

        Binding {
            target: sceneCombo
            property: "currentIndex"
            value: storyBoardViewModel ? storyBoardViewModel.currentSceneIndex : 0
            when: storyBoardViewModel !== null
        }

        Rectangle {
            visible: storyBoardViewModel && storyBoardViewModel.sceneLabels.length === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"

            Label {
                anchors.centerIn: parent
                width: parent.width - 32
                text: storyBoardViewModel ? storyBoardViewModel.emptyMessage : ""
                color: "#9a9a9a"
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }

        ScrollView {
            id: scrollView
            visible: storyBoardViewModel && storyBoardViewModel.sceneLabels.length > 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            GridLayout {
                id: grid
                width: scrollView.availableWidth > 0 ? scrollView.availableWidth : root.width
                columns: 2
                rowSpacing: 14
                columnSpacing: 14

                Repeater {
                    model: shotModel

                    Rectangle {
                        id: cell
                        Layout.fillWidth: true
                        Layout.minimumWidth: (grid.width - grid.columnSpacing) / 2 - 1
                        property string shotId: model.shotId !== undefined ? model.shotId : ""
                        property bool shotSelected: storyBoardViewModel
                            && model.shotId !== undefined
                            && storyBoardViewModel.selectedShotId === model.shotId
                        color: "#25262a"
                        border.color: shotSelected ? "#4080ff" : "#4a4d57"
                        border.width: shotSelected ? 2 : 1
                        radius: 10
                        implicitHeight: cellCol.implicitHeight + 20

                        ColumnLayout {
                            id: cellCol
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 10
                            spacing: 8

                            Item {
                                Layout.fillWidth: true
                                implicitHeight: topCol.height

                                Column {
                                    id: topCol
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    spacing: 8

                                    Label {
                                        width: topCol.width
                                        text: model.headerLine !== undefined ? model.headerLine : ""
                                        color: "#e8e8e8"
                                        font.pixelSize: 12
                                        font.bold: true
                                        wrapMode: Text.WordWrap
                                    }

                                    Label {
                                        property string subLineText: model.subLine !== undefined ? model.subLine : ""
                                        visible: subLineText.length > 0
                                        width: topCol.width
                                        height: 36
                                        text: subLineText
                                        color: "#888888"
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                        elide: Text.ElideRight
                                        clip: true
                                    }

                                    Rectangle {
                                        width: topCol.width
                                        height: 200
                                        color: "#1a1b1e"
                                        radius: 6
                                        clip: true

                                        Image {
                                            id: kmImage
                                            anchors.fill: parent
                                            fillMode: Image.PreserveAspectFit  // Fit to show complete image centered
                                            source: (model.imageUrl !== undefined && model.imageUrl) ? model.imageUrl : ""
                                            asynchronous: true
                                            visible: source !== ""
                                        }

                                        Label {
                                            anchors.centerIn: parent
                                            visible: kmImage.source === "" || kmImage.status === Image.Error
                                            text: "No key frame"
                                            color: "#555555"
                                            font.pixelSize: 11
                                        }
                                    }
                                }

                                MouseArea {
                                    anchors.fill: topCol
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (storyBoardViewModel && model.shotId !== undefined)
                                            storyBoardViewModel.select_shot(model.shotId)
                                    }
                                }
                            }

                            TextArea {
                                id: shotNotes
                                Layout.fillWidth: true
                                Layout.minimumHeight: 96
                                placeholderText: "Shot notes (markdown body)…"
                                color: "#e0e0e0"
                                wrapMode: TextArea.Wrap
                                selectByMouse: true
                                text: model.bodyText !== undefined ? model.bodyText : ""
                                background: Rectangle {
                                    color: "#1e1f22"
                                    border.color: "#3d3d3d"
                                    radius: 4
                                }
                                onEditingFinished: {
                                    if (storyBoardViewModel && model.shotId !== undefined)
                                        storyBoardViewModel.save_shot_body(model.shotId, shotNotes.text)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
