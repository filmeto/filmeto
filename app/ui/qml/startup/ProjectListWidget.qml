import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

/* Matches pre-QML ProjectListWidget: header 80px + gradient logo, list rows, toolbar add button */
Rectangle {
    id: root
    color: "transparent"
    property var bridge: projectListBridge

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        /* Header: project_list_header, fixed 80, margins 16 */
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                anchors.topMargin: 16
                anchors.bottomMargin: 16
                spacing: 12

                Rectangle {
                    width: 40
                    height: 40
                    radius: 8
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#4080ff" }
                        GradientStop { position: 1.0; color: "#8040ff" }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "A"
                        color: "white"
                        font.pixelSize: 20
                        font.bold: true
                    }
                }

                Label {
                    text: "AniMaker"
                    color: "#E1E1E1"
                    font.pixelSize: 20
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "rgba(60,63,65,0.5)"
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

                HoverHandler {
                    id: rowHover
                }

                color: selected ? "rgba(61,79,124,0.6)" : (rowHover.hovered ? "rgba(60,63,65,0.5)" : "transparent")
                border.color: selected ? "#4080ff" : "transparent"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    anchors.topMargin: 8
                    anchors.bottomMargin: 8
                    spacing: 10

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 32
                        TapHandler {
                            onTapped: if (bridge) bridge.select_project(modelData.name)
                        }
                        RowLayout {
                            anchors.fill: parent
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
                        }
                    }

                    ToolButton {
                        id: editBtn
                        visible: selected || rowHover.hovered
                        width: 24
                        height: 24
                        flat: true
                        text: "\ue601"
                        font.family: "iconfont"
                        font.pixelSize: 14
                        hoverEnabled: true
                        background: Rectangle { color: "transparent" }
                        contentItem: Text {
                            text: editBtn.text
                            font: editBtn.font
                            color: editBtn.hovered ? "#4080ff" : "#888888"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: if (bridge) bridge.request_edit(modelData.name)
                    }
                }
            }
        }

        /* project_list_toolbar: height 56, border-top rgba(60,63,65,0.5) */
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "transparent"

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                color: "rgba(60,63,65,0.5)"
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.topMargin: 8
                anchors.bottomMargin: 8
                spacing: 8

                ToolButton {
                    id: addBtn
                    width: 40
                    height: 40
                    flat: true
                    text: "\ue6b3"
                    font.family: "iconfont"
                    font.pixelSize: 18
                    hoverEnabled: true
                    background: Rectangle {
                        radius: 6
                        color: addBtn.pressed ? "rgba(44,47,49,0.8)"
                             : (addBtn.hovered ? "rgba(76,80,82,0.8)" : "rgba(60,63,65,0.6)")
                    }
                    contentItem: Text {
                        text: addBtn.text
                        font: addBtn.font
                        color: "#E1E1E1"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: if (bridge) bridge.request_create_project()
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
