// WorkflowsTab.qml - Workflows Management Tab
// Contains workflow list with Edit and Config functionality

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import "dialogs" as Dialogs

Item {
    id: root

    property var configModel: null

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // Header
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            Label {
                text: "Workflows Management"
                font.bold: true
                font.pixelSize: 16
                color: "#e0e0e0"
                Layout.fillWidth: true
            }

            Label {
                text: "Manage ComfyUI workflows for different generation types"
                font.pixelSize: 12
                color: "#808080"
                Layout.fillWidth: true
            }
        }

        // Toolbar
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: qsTr("+ Add Workflow")
                implicitHeight: 28

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

                onClicked: {
                    fileDialog.open()
                }
            }

            Item { Layout.fillWidth: true }
        }

        // Workflow List
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#2d2d2d"
            border.color: "#3a3a3a"
            border.width: 1
            radius: 4

            ListView {
                id: workflowList
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                spacing: 4

                model: configModel ? configModel.workflows : []

                delegate: WorkflowItemDelegate {
                    width: workflowList.width - 8
                    workflowData: modelData

                    onEditClicked: {
                        var workflowType = workflowData.type
                        var result = configModel.get_workflow_json(workflowType)
                        jsonEditorDialog.workflowType = workflowType
                        jsonEditorDialog.jsonContent = result.content
                        jsonEditorDialog.open()
                    }

                    onConfigClicked: {
                        var workflowType = workflowData.type
                        var nodes = configModel.get_workflow_nodes(workflowType)
                        var currentConfig = workflowData.node_mapping || {}

                        configDialog.workflowType = workflowType
                        configDialog.workflowName = workflowData.name
                        configDialog.nodes = nodes
                        configDialog.currentMapping = currentConfig
                        configDialog.open()
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }
            }
        }
    }

    // File dialog for importing workflows
    FileDialog {
        id: fileDialog
        title: qsTr("Select Workflow File")
        nameFilters: ["JSON Files (*.json)", "All Files (*)"]
        onAccepted: {
            // Handle file import
            console.log("Selected file:", selectedFile)
        }
    }

    // Workflow Config Dialog
    Dialogs.WorkflowConfigDialog {
        id: configDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: 700
        height: 800
        modal: true

        onAccepted: {
            if (configModel) {
                var mappingJson = JSON.stringify({
                    input_node: inputNode,
                    prompt_node: promptNode,
                    output_node: outputNode,
                    seed_node: seedNode
                })
                configModel.save_workflow_config(workflowType, workflowName, mappingJson)
            }
        }
    }

    // Workflow JSON Editor Dialog
    Dialogs.WorkflowJsonEditorDialog {
        id: jsonEditorDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: 800
        height: 600
        modal: true

        onAccepted: {
            if (configModel) {
                configModel.save_workflow_json(workflowType, jsonContent)
            }
        }
    }

    // Connections to model signals
    Connections {
        target: configModel
        function onWorkflowSaved(workflowType) {
            console.log("Workflow saved:", workflowType)
        }
        function onWorkflowError(errorMessage) {
            errorDialog.text = errorMessage
            errorDialog.open()
        }
    }

    // Error Dialog
    Dialog {
        id: errorDialog
        property alias text: errorLabel.text
        title: qsTr("Error")
        modal: true
        anchors.centerIn: parent
        standardButtons: Dialog.Ok

        Label {
            id: errorLabel
            color: "#e74c3c"
            wrapMode: Text.WordWrap
        }
    }
}