import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/* Colors aligned with main window: top_side_bar main_window_top_bar_button + dark_style QPushButton */
Rectangle {
    id: root
    color: "transparent"
    property var bridge: projectListBridge

    /* Same chrome as MainWindowTopSideBar settings / language buttons (#3c3f41, #555555, hover #4c5052) */
    component TopChromeButton: ToolButton {
        id: btn
        implicitWidth: 32
        implicitHeight: 32
        flat: true
        font.family: "iconfont"
        font.pixelSize: 14
        hoverEnabled: true
        background: Rectangle {
            radius: 4
            border.width: 1
            border.color: "#555555"
            color: btn.pressed ? "#2c2f31" : (btn.hovered ? "#4c5052" : "#3c3f41")
        }
        contentItem: Text {
            text: btn.text
            font: btn.font
            color: "#ffffff"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                Rectangle {
                    width: 32
                    height: 32
                    radius: 6
                    color: "#4080ff"
                    Text {
                        anchors.centerIn: parent
                        text: "F"
                        color: "white"
                        font.pixelSize: 16
                        font.bold: true
                    }
                }

                Label {
                    text: "Filmeto"
                    color: "#E1E1E1"
                    font.pixelSize: 14
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#505254"
        }

        ListView {
            id: projectList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 4
            model: bridge ? bridge.projects : []
            boundsBehavior: Flickable.StopAtBounds
            leftMargin: 8
            rightMargin: 8
            topMargin: 8
            bottomMargin: 8

            delegate: Rectangle {
                required property var modelData
                required property int index
                readonly property bool selected: bridge && bridge.selectedProject === modelData.name

                width: projectList.width - 16
                height: 48
                radius: 6
                color: selected ? "rgba(61,79,124,0.6)" : (ma.containsMouse ? "rgba(60,63,65,0.5)" : "transparent")
                border.color: selected ? "#4080ff" : "transparent"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 8
                    spacing: 10

                    Rectangle {
                        width: 32
                        height: 32
                        radius: 16
                        color: "#4080ff"
                        Text {
                            anchors.centerIn: parent
                            text: (modelData.name && modelData.name.length > 0) ? modelData.name.charAt(0).toUpperCase() : "P"
                            color: "white"
                            font.pixelSize: 14
                            font.bold: true
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.name
                        color: "#E1E1E1"
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }

                    TopChromeButton {
                        visible: selected || ma.containsMouse
                        text: "\ue601"
                        onClicked: if (bridge) bridge.request_edit(modelData.name)
                    }
                }

                MouseArea {
                    id: ma
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: if (bridge) bridge.select_project(modelData.name)
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 52
            color: "transparent"
            border.color: "#505254"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                TopChromeButton {
                    text: "\ue6b3"
                    onClicked: if (bridge) bridge.request_create_project()
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
