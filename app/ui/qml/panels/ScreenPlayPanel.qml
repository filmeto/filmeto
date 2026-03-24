import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

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

                    ToolButton {
                        text: "\ue835"
                        font.family: "iconfont"
                        font.pixelSize: 16
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_add_scene_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Add Scene"
                    }

                    ToolButton {
                        text: "\ue6b8"
                        font.family: "iconfont"
                        font.pixelSize: 16
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
                        border.color: "#2f2f2f"

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

                    ToolButton {
                        text: "\ue64f"
                        font.family: "iconfont"
                        font.pixelSize: 16
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_return_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Return to List"
                    }

                    ToolButton {
                        text: "\ue654"
                        font.family: "iconfont"
                        font.pixelSize: 16
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_save_clicked()
                        ToolTip.visible: hovered
                        ToolTip.text: "Save Scene"
                    }

                    ToolButton {
                        text: "\ue702"
                        font.family: "iconfont"
                        font.pixelSize: 16
                        onClicked: root.insertIntoEditor("\nACTION DESCRIPTION GOES HERE.\n")
                        ToolTip.visible: hovered
                        ToolTip.text: "Action"
                    }

                    ToolButton {
                        text: "\ue60c"
                        font.family: "iconfont"
                        font.pixelSize: 16
                        onClicked: root.insertIntoEditor("\nCHARACTER_NAME\n")
                        ToolTip.visible: hovered
                        ToolTip.text: "Character"
                    }

                    ToolButton {
                        text: "\ue721"
                        font.family: "iconfont"
                        font.pixelSize: 16
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
