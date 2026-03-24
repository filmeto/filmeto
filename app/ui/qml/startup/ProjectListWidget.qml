import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "transparent"
    property var bridge: projectListBridge

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 10

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
                color: selected ? "rgba(61,79,124,0.6)" : (ma.containsMouse ? "rgba(60,63,65,0.5)" : "transparent")
                border.color: selected ? "#4080ff" : "transparent"
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
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

                    ToolButton {
                        visible: selected || ma.containsMouse
                        text: "\ue601"
                        font.family: "iconfont"
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
            Layout.preferredHeight: 56
            color: "transparent"
            border.color: "rgba(60,63,65,0.5)"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                ToolButton {
                    text: "\ue6b3"
                    font.family: "iconfont"
                    onClicked: if (bridge) bridge.request_create_project()
                }
                Item { Layout.fillWidth: true }
            }
        }
    }
}
