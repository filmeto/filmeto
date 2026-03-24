import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    color: "#1e1f22"
    radius: 10
    border.color: "#505254"
    border.width: 1

    property var bridge: startupBridge

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "#3d3f4e"
            radius: 10

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Label {
                    text: bridge ? bridge.title : "Filmeto"
                    color: "#E1E1E1"
                    font.pixelSize: 14
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
                ToolButton {
                    text: "\u2699"
                    onClicked: if (bridge) bridge.open_settings()
                }
                ToolButton {
                    text: "\ud83d\udda5"
                    onClicked: if (bridge) bridge.open_server_dialog()
                }
                ToolButton {
                    text: "✕"
                    onClicked: if (bridge) bridge.close_window()
                }
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                property point dragStart: Qt.point(0, 0)
                onPressed: function(mouse) { dragStart = Qt.point(mouse.x, mouse.y) }
                onPositionChanged: function(mouse) {
                    if ((mouse.buttons & Qt.LeftButton) === 0) return
                    var dx = mouse.x - dragStart.x
                    var dy = mouse.y - dragStart.y
                    root.Window.window.x += dx
                    root.Window.window.y += dy
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                color: "#2b2d30"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    anchors.margins: 12

                    Label {
                        text: "Projects"
                        color: "#E1E1E1"
                        font.bold: true
                        font.pixelSize: 15
                    }

                    ListView {
                        id: projectList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        model: bridge ? bridge.projects : []
                        clip: true
                        spacing: 4

                        delegate: Rectangle {
                            required property var modelData
                            readonly property bool selected: bridge && bridge.selectedProject === modelData.name
                            width: projectList.width
                            height: 40
                            radius: 6
                            color: selected ? "rgba(61,79,124,0.6)" : (ma.containsMouse ? "rgba(60,63,65,0.5)" : "transparent")
                            border.color: selected ? "#4080ff" : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 8
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: "#E1E1E1"
                                    elide: Text.ElideRight
                                }
                                ToolButton {
                                    text: "\ue61e"
                                    font.family: "iconfont"
                                    onClicked: if (bridge) bridge.edit_project(modelData.name)
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

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: createInput
                            Layout.fillWidth: true
                            placeholderText: "New project name"
                        }
                        Button {
                            text: "+"
                            onClicked: if (bridge) bridge.create_project(createInput.text)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#1e1f22"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10

                    ColumnLayout {
                        Layout.preferredWidth: 36
                        Layout.fillHeight: true
                        spacing: 12
                        Repeater {
                            model: [
                                { panel: "members", icon: "\ue89e" },
                                { panel: "screenplay", icon: "\ue993" },
                                { panel: "plan", icon: "\ue8a5" }
                            ]
                            delegate: ToolButton {
                                required property var modelData
                                checkable: true
                                checked: bridge && bridge.activePanel === modelData.panel
                                text: modelData.icon
                                font.family: "iconfont"
                                onClicked: if (bridge) bridge.set_active_panel(modelData.panel)
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10

                        Label {
                            text: bridge && bridge.selectedProject ? bridge.selectedProject : "No project selected"
                            color: "#E1E1E1"
                            font.pixelSize: 20
                            font.bold: true
                        }

                        Label {
                            text: "Project overview"
                            color: "#A0A0A0"
                        }
                        Label {
                            text: "Active panel: " + (bridge ? bridge.activePanelTitle : "Panel")
                            color: "#7fa8ff"
                        }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        radius: 6
                        color: "#2b2d30"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Label { text: "Timeline"; color: "#A0A0A0" }
                            Item { Layout.fillWidth: true }
                            Label { text: bridge ? bridge.timelineCount : "0"; color: "#E1E1E1"; font.bold: true }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        radius: 6
                        color: "#2b2d30"
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Label { text: "Tasks"; color: "#A0A0A0" }
                            Item { Layout.fillWidth: true }
                            Label { text: bridge ? bridge.taskCount : "0"; color: "#E1E1E1"; font.bold: true }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        radius: 6
                        color: "#2b2d30"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Label { text: "Budget"; color: "#A0A0A0" }
                            Label { text: bridge ? bridge.budgetText : "$0.00 / $0.00"; color: "#E1E1E1" }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 6
                        color: "#2b2d30"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 10
                            Label { text: "Story"; color: "#A0A0A0" }
                            Label {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                wrapMode: Text.Wrap
                                text: bridge ? bridge.storyDescription : ""
                                color: "#E1E1E1"
                            }
                        }
                    }

                        RowLayout {
                            spacing: 8
                            Button {
                                text: "Refresh"
                                onClicked: if (bridge) bridge.refresh_projects()
                            }
                            Button {
                                text: "Edit Selected"
                                enabled: bridge && bridge.selectedProject
                                onClicked: if (bridge && bridge.selectedProject) bridge.edit_project(bridge.selectedProject)
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }
}
