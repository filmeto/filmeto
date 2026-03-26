import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common/buttons" as CommonButtons
import "../common/inputs" as CommonInputs

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

        // List Page
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

                    CommonButtons.IconButton {
                        iconCode: "\ue835"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Add Scene")
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_add_scene_clicked()
                    }

                    CommonButtons.IconButton {
                        iconCode: "\ue6b8"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Refresh")
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_refresh_clicked()
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                // Empty state
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

        // Editor Page
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

                    CommonButtons.IconButton {
                        iconCode: "\ue64f"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Return to List")
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_return_clicked()
                    }

                    CommonButtons.IconButton {
                        iconCode: "\ue654"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Save Scene")
                        onClicked: if (screenPlayViewModel) screenPlayViewModel.on_save_clicked()
                    }

                    CommonButtons.IconButton {
                        iconCode: "\ue702"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Action")
                        onClicked: root.insertIntoEditor("\nACTION DESCRIPTION GOES HERE.\n")
                    }

                    CommonButtons.IconButton {
                        iconCode: "\ue60c"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Character")
                        onClicked: root.insertIntoEditor("\nCHARACTER_NAME\n")
                    }

                    CommonButtons.IconButton {
                        iconCode: "\ue721"
                        iconFontFamily: "iconfont"
                        tooltip: qsTr("Dialogue")
                        onClicked: root.insertIntoEditor("\nWhat the character says here.\n")
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                CommonInputs.TextArea {
                    id: editor
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 8
                    Layout.rightMargin: 8
                    Layout.bottomMargin: 8
                    text: screenPlayViewModel ? screenPlayViewModel.editorText : ""
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
