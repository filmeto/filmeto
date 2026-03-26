// WorkflowItemDelegate.qml - Delegate for workflow list items
// Displays workflow info with Edit and Config buttons

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var workflowData: ({})

    signal editClicked()
    signal configClicked()

    implicitHeight: 72
    color: mouseArea.containsMouse ? "#303030" : "#252525"
    radius: 4
    border.color: "#3a3a3a"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 14

        // Workflow Info
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            Label {
                text: workflowData.name || "Unnamed Workflow"
                font.bold: true
                font.pixelSize: 12
                color: "#ffffff"
                Layout.fillWidth: true
                elide: Text.ElideRight
            }

            Label {
                text: {
                    var typeText = "Type: " + (workflowData.type || "Unknown")
                    if (workflowData.description) {
                        typeText += " • " + workflowData.description
                    }
                    if (workflowData.is_builtin) {
                        typeText += " (builtin)"
                    }
                    return typeText
                }
                font.pixelSize: 10
                color: "#888888"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
            }
        }

        // Action Buttons
        RowLayout {
            spacing: 8

            Button {
                text: qsTr("Edit")
                implicitWidth: 65
                implicitHeight: 30

                background: Rectangle {
                    color: parent.hovered ? "#666666" : "#555555"
                    radius: 4
                }

                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 11
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: root.editClicked()
            }

            Button {
                text: qsTr("Config")
                implicitWidth: 65
                implicitHeight: 30

                background: Rectangle {
                    color: parent.hovered ? "#5dade2" : "#3498db"
                    radius: 4
                }

                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 11
                    font.bold: true
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                onClicked: root.configClicked()
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }
}