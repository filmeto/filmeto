import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "transparent"
    property var bridge: projectInfoBridge

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: root.width
            spacing: 12
            anchors.margins: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                color: "#1e1f22"
                radius: 8
                border.color: "#505254"
                border.width: 1

                Label {
                    anchors.centerIn: parent
                    text: bridge && bridge.videoText ? bridge.videoText : "No Video Preview"
                    color: "#999999"
                }

                RowLayout {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    Label {
                        Layout.fillWidth: true
                        text: bridge ? bridge.projectName : ""
                        elide: Text.ElideRight
                        color: "#E1E1E1"
                        font.bold: true
                    }
                    Button {
                        text: bridge ? bridge.editLabel : "Edit"
                        onClicked: if (bridge) bridge.request_edit()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    radius: 8
                    color: "#2b2d30"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        Label { text: bridge ? bridge.timelineLabel : "Timeline Items"; color: "#A0A0A0" }
                        Label { text: bridge ? bridge.timelineCount : "0"; color: "#E1E1E1"; font.bold: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    radius: 8
                    color: "#2b2d30"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        Label { text: bridge ? bridge.taskLabel : "Task Count"; color: "#A0A0A0" }
                        Label { text: bridge ? bridge.taskCount : "0"; color: "#E1E1E1"; font.bold: true }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 84
                radius: 8
                color: "#2b2d30"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6
                    Label { text: bridge ? bridge.budgetLabel : "Budget Usage"; color: "#A0A0A0" }
                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: bridge ? bridge.budgetPercent : 0
                    }
                    Label { text: bridge ? bridge.budgetText : "$0.00 / $0.00"; color: "#E1E1E1" }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 140
                radius: 8
                color: "#2b2d30"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6
                    Label { text: bridge ? bridge.storyLabel : "Story Description"; color: "#A0A0A0" }
                    Label {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        wrapMode: Text.Wrap
                        text: bridge ? bridge.storyDescription : ""
                        color: "#E1E1E1"
                    }
                }
            }
        }
    }
}
