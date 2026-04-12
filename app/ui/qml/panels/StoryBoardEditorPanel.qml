import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    anchors.fill: parent
    color: "#1e1e1e"

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
                Layout.fillWidth: true
                visible: storyBoardViewModel && storyBoardViewModel.sceneLabels.length > 0
                model: storyBoardViewModel ? storyBoardViewModel.sceneLabels : []
                currentIndex: storyBoardViewModel ? storyBoardViewModel.currentSceneIndex : 0
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
                                        text: subLineText
                                        color: "#888888"
                                        font.pixelSize: 10
                                        wrapMode: Text.WordWrap
                                        maximumHeight: 36
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
                                            fillMode: Image.PreserveAspectCrop
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
