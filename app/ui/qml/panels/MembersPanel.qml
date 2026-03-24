import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            Layout.topMargin: 8
            spacing: 6

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: membersViewModel ? membersViewModel.searchPlaceholder : ""
                onTextChanged: membersModel.set_filter(text)
            }

            ToolButton {
                text: ""
                font.family: "iconfont"
                font.pixelSize: 16
                onClicked: if (membersViewModel) membersViewModel.on_add_member_clicked()
                ToolTip.visible: hovered && membersViewModel && membersViewModel.addTooltip
                ToolTip.text: membersViewModel ? membersViewModel.addTooltip : ""
            }
        }

        ListView {
            id: membersList
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 6
            Layout.rightMargin: 6
            Layout.bottomMargin: 6
            clip: true
            spacing: 4
            model: membersModel

            delegate: Item {
                width: ListView.view.width
                height: visible ? 52 : 0
                visible: model.visible

                Rectangle {
                    anchors.fill: parent
                    radius: 6
                    color: rowMouse.containsMouse ? "#2b2b2b" : "#242424"
                    border.color: rowMouse.containsMouse ? "#3c3c3c" : "#2a2a2a"
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 10

                    Rectangle {
                        width: 28
                        height: 28
                        radius: 14
                        color: model.color || "#4a90e2"
                        Layout.alignment: Qt.AlignVCenter

                        Text {
                            anchors.centerIn: parent
                            text: model.icon || "A"
                            color: "white"
                            font.bold: true
                            font.pixelSize: 13
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: model.name
                            color: "#ffffff"
                            font.bold: true
                            font.pixelSize: 14
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Text {
                            text: model.title
                            color: "#cccccc"
                            font.pixelSize: 12
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    Text {
                        visible: model.active
                        text: "..."
                        color: model.color || "#4a90e2"
                        font.pixelSize: 18
                        font.bold: true
                        Layout.alignment: Qt.AlignVCenter
                    }
                }

                MouseArea {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: if (membersViewModel) membersViewModel.on_member_clicked(model.key)
                    onDoubleClicked: if (membersViewModel) membersViewModel.on_member_double_clicked(model.key)
                }
            }
        }
    }
}
