import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent
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

    function insertIntoEditor(snippet) {
        if (!editor) {
            return
        }
        var current = editor.text || ""
        var pos = editor.cursorPosition
        var prefix = current.slice(0, pos)
        var suffix = current.slice(pos)
        editor.text = prefix + snippet + suffix
        editor.cursorPosition = pos + snippet.length
    }

    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: screenPlayViewModel && screenPlayViewModel.mode === "editor" ? 1 : 0

        Item {
            id: listPage

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 8
                    Layout.rightMargin: 8
                    Layout.topMargin: 8
                    Layout.bottomMargin: 8
                    spacing: 6

                    IconToolButton {
                        text: "\ue835"
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_add_scene_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Add Scene"
                    }

                    IconToolButton {
                        text: "\ue6b8"
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_refresh_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Refresh"
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    visible: screenPlayModel && screenPlayModel.count === 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: screenPlayViewModel ? screenPlayViewModel.emptyMessage : ""
                        color: "#9a9a9a"
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                ListView {
                    id: sceneList
                    visible: screenPlayModel && screenPlayModel.count > 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 8
                    Layout.rightMargin: 8
                    Layout.bottomMargin: 8
                    clip: true
                    spacing: 6
                    model: screenPlayModel

                    delegate: Rectangle {
                        width: ListView.view.width
                        height: 64
                        radius: 8
                        color: rowMouse.pressed ? "#414141" : (rowMouse.containsMouse ? "#3f3f3f" : "#363636")
                        border.color: (screenPlayViewModel && screenPlayViewModel.selectedSceneId === model.sceneId) ? "#4080ff" : "#2f2f2f"
                        border.width: (screenPlayViewModel && screenPlayViewModel.selectedSceneId === model.sceneId) ? 3 : 1

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            anchors.topMargin: 8
                            anchors.bottomMargin: 8
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: model.title
                                color: "#f0f0f0"
                                font.pixelSize: 13
                                font.bold: true
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: model.overview
                                color: "#c0c0c0"
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                        }

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: if (screenPlayViewModel) screenPlayViewModel.on_scene_clicked(model.sceneId)
                        }
                    }
                }
            }
        }

        Item {
            id: editorPage

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: 8
                    Layout.rightMargin: 8
                    Layout.topMargin: 8
                    Layout.bottomMargin: 8
                    spacing: 6

                    IconToolButton {
                        text: "\ue64f"
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_return_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Return to List"
                    }

                    IconToolButton {
                        text: "\ue654"
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_save_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Save Scene"
                    }

                    IconToolButton {
                        text: "\ue702"
                        onClicked: root.insertIntoEditor("\nACTION DESCRIPTION GOES HERE.\n")
                        ToolTip.visible: hovered
                        ToolTip.text: "Action"
                    }

                    IconToolButton {
                        text: "\ue60c"
                        onClicked: root.insertIntoEditor("\nCHARACTER_NAME\n")
                        ToolTip.visible: hovered
                        ToolTip.text: "Character"
                    }

                    IconToolButton {
                        text: "\ue721"
                        onClicked: root.insertIntoEditor("\nWhat the character says here.\n")
                        ToolTip.visible: hovered
                        ToolTip.text: "Dialogue"
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                TextArea {
                    id: editor
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 8
                    Layout.rightMargin: 8
                    Layout.bottomMargin: 8
                    text: screenPlayViewModel ? screenPlayViewModel.editorText : ""
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    color: "#f0f0f0"
                    selectionColor: "#4a90e2"
                    selectedTextColor: "#ffffff"
                    font.pixelSize: 13
                    background: Rectangle {
                        radius: 6
                        color: "#2b2b2b"
                        border.color: "#202020"
                    }
                    onTextChanged: if (screenPlayViewModel) screenPlayViewModel.on_editor_text_changed(text)

                    Connections {
                        target: screenPlayViewModel
                        function onEditorTextUpdated(value) {
                            if (editor.text !== value) {
                                editor.text = value
                            }
                        }
                    }
                }
            }
        }
    }
}
