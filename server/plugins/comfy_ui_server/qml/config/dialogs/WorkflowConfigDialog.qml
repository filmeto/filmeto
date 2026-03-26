// WorkflowConfigDialog.qml - Dialog for configuring workflow node mappings
// Allows selection of input, prompt, output, and seed nodes

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: root

    // Properties to be set before opening
    property string workflowType: ""
    property string workflowName: ""
    property var nodes: []  // List of {id, class_type}
    property var currentMapping: ({})

    // Result properties
    property string inputNode: ""
    property string promptNode: ""
    property string outputNode: ""
    property string seedNode: ""

    title: qsTr("Configure Workflow")
    modal: true
    standardButtons: Dialog.Cancel | Dialog.Save

    // Reset properties when opened
    onOpened: {
        nameField.text = workflowName
        typeCombo.currentIndex = typeCombo.indexOfValue(workflowType)

        // Set current mappings
        inputNode = currentMapping.input_node || ""
        promptNode = currentMapping.prompt_node || ""
        outputNode = currentMapping.output_node || ""
        seedNode = currentMapping.seed_node || ""

        updateComboSelection(inputNodeCombo, inputNode)
        updateComboSelection(promptNodeCombo, promptNode)
        updateComboSelection(outputNodeCombo, outputNode)
        updateComboSelection(seedNodeCombo, seedNode)
    }

    // Center in parent
    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2

    background: Rectangle {
        color: "#2d2d2d"
        border.color: "#3a3a3a"
        border.width: 1
        radius: 6
    }

    header: Rectangle {
        color: "#252525"
        implicitHeight: 50
        radius: 6

        // Bottom corners fix
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 6
            color: parent.color
        }

        Label {
            text: root.title
            font.bold: true
            font.pixelSize: 14
            color: "#ffffff"
            anchors.centerIn: parent
        }
    }

    footer: DialogButtonBox {
        background: Rectangle {
            color: "#252525"
            radius: 6

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 6
                color: parent.color
            }
        }

        buttonLayout: DialogButtonBox.Horizontal

        Button {
            text: qsTr("Cancel")
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole

            background: Rectangle {
                implicitHeight: 32
                color: parent.hovered ? "#555555" : "#444444"
                radius: 4
            }

            contentItem: Text {
                text: parent.text
                font.pixelSize: 12
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        Button {
            text: qsTr("Save Workflow")
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole

            background: Rectangle {
                implicitHeight: 32
                color: parent.hovered ? "#5dade2" : "#3498db"
                radius: 4
            }

            contentItem: Text {
                text: parent.text
                font.pixelSize: 12
                font.bold: true
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    // Helper function to update combo selection
    function updateComboSelection(combo, nodeId) {
        for (var i = 0; i < combo.count; i++) {
            var itemValue = combo.model[i].value
            if (itemValue === nodeId) {
                combo.currentIndex = i
                return
            }
        }
        combo.currentIndex = 0  // None
    }

    // Helper to get node ID from combo
    function getNodeIdFromCombo(combo) {
        if (combo.currentIndex <= 0) return ""
        return combo.model[combo.currentIndex].value
    }

    // Build node options for combos
    property var nodeOptions: {
        var options = [{text: "None", value: ""}]
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i]
            options.push({
                text: node.id + " - " + node.class_type,
                value: node.id
            })
        }
        return options
    }

    contentItem: ScrollView {
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: 650
            spacing: 20

            // File info
            Label {
                text: qsTr("Workflow: ") + workflowType
                font.pixelSize: 12
                color: "#888888"
            }

            // Basic Info Section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: basicInfoLayout.implicitHeight + 20
                color: "#252525"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: basicInfoLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: qsTr("Basic Information")
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // Name
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Name *")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        TextField {
                            id: nameField
                            Layout.fillWidth: true
                            text: workflowName
                            selectByMouse: true
                            implicitHeight: 32

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: nameField.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            color: "#ffffff"
                            placeholderTextColor: "#606060"
                            placeholderText: qsTr("Enter workflow name")

                            onTextChanged: workflowName = text
                        }
                    }

                    // Type
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Tool Type *")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: typeCombo
                            Layout.fillWidth: true
                            implicitHeight: 32
                            model: [
                                {text: "text2image", value: "text2image"},
                                {text: "image2image", value: "image2image"},
                                {text: "image2video", value: "image2video"},
                                {text: "text2video", value: "text2video"},
                                {text: "speak2video", value: "speak2video"},
                                {text: "text2speak", value: "text2speak"},
                                {text: "text2music", value: "text2music"},
                                {text: "custom", value: "custom"}
                            ]
                            textRole: "text"
                            valueRole: "value"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: typeCombo.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: Text {
                                text: typeCombo.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            delegate: ItemDelegate {
                                width: typeCombo.width
                                height: 30

                                contentItem: Text {
                                    text: modelData.text
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#cccccc"
                                    verticalAlignment: Text.AlignVCenter
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#2d2d2d"
                                }

                                highlighted: typeCombo.highlightedIndex === index
                            }

                            popup: Popup {
                                y: typeCombo.height
                                width: typeCombo.width
                                implicitHeight: contentItem.implicitHeight
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: typeCombo.popup.visible ? typeCombo.delegateModel : null
                                    currentIndex: typeCombo.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }
                            }

                            onCurrentValueChanged: {
                                if (currentValue) {
                                    workflowType = currentValue
                                }
                            }

                            function indexOfValue(value) {
                                for (var i = 0; i < model.length; i++) {
                                    if (model[i].value === value) return i
                                }
                                return 0
                            }
                        }
                    }
                }
            }

            // Node Mapping Section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: nodeMappingLayout.implicitHeight + 20
                color: "#252525"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: nodeMappingLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: qsTr("Node Mapping")
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // Input Node
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Input Node")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: inputNodeCombo
                            Layout.fillWidth: true
                            implicitHeight: 32
                            model: root.nodeOptions
                            textRole: "text"
                            valueRole: "value"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: inputNodeCombo.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: Text {
                                text: inputNodeCombo.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            delegate: ItemDelegate {
                                width: inputNodeCombo.width
                                height: 30

                                contentItem: Text {
                                    text: modelData.text
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#cccccc"
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#2d2d2d"
                                }

                                highlighted: inputNodeCombo.highlightedIndex === index
                            }

                            popup: Popup {
                                y: inputNodeCombo.height
                                width: inputNodeCombo.width
                                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: inputNodeCombo.popup.visible ? inputNodeCombo.delegateModel : null
                                    currentIndex: inputNodeCombo.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }
                            }
                        }

                        Label {
                            text: qsTr("Node that receives input images/videos")
                            font.pixelSize: 10
                            color: "#666666"
                        }
                    }

                    // Prompt Node
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Prompt Node *")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: promptNodeCombo
                            Layout.fillWidth: true
                            implicitHeight: 32
                            model: root.nodeOptions
                            textRole: "text"
                            valueRole: "value"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: promptNodeCombo.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: Text {
                                text: promptNodeCombo.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            delegate: ItemDelegate {
                                width: promptNodeCombo.width
                                height: 30

                                contentItem: Text {
                                    text: modelData.text
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#cccccc"
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#2d2d2d"
                                }

                                highlighted: promptNodeCombo.highlightedIndex === index
                            }

                            popup: Popup {
                                y: promptNodeCombo.height
                                width: promptNodeCombo.width
                                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: promptNodeCombo.popup.visible ? promptNodeCombo.delegateModel : null
                                    currentIndex: promptNodeCombo.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }
                            }
                        }

                        Label {
                            text: qsTr("Node that receives text prompts")
                            font.pixelSize: 10
                            color: "#666666"
                        }
                    }

                    // Output Node
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Output Node *")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: outputNodeCombo
                            Layout.fillWidth: true
                            implicitHeight: 32
                            model: root.nodeOptions
                            textRole: "text"
                            valueRole: "value"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: outputNodeCombo.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: Text {
                                text: outputNodeCombo.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            delegate: ItemDelegate {
                                width: outputNodeCombo.width
                                height: 30

                                contentItem: Text {
                                    text: modelData.text
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#cccccc"
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#2d2d2d"
                                }

                                highlighted: outputNodeCombo.highlightedIndex === index
                            }

                            popup: Popup {
                                y: outputNodeCombo.height
                                width: outputNodeCombo.width
                                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: outputNodeCombo.popup.visible ? outputNodeCombo.delegateModel : null
                                    currentIndex: outputNodeCombo.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }
                            }
                        }

                        Label {
                            text: qsTr("Node that produces final output")
                            font.pixelSize: 10
                            color: "#666666"
                        }
                    }

                    // Seed Node
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: qsTr("Seed Node")
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: seedNodeCombo
                            Layout.fillWidth: true
                            implicitHeight: 32
                            model: root.nodeOptions
                            textRole: "text"
                            valueRole: "value"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: seedNodeCombo.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: Text {
                                text: seedNodeCombo.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            delegate: ItemDelegate {
                                width: seedNodeCombo.width
                                height: 30

                                contentItem: Text {
                                    text: modelData.text
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#cccccc"
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#2d2d2d"
                                }

                                highlighted: seedNodeCombo.highlightedIndex === index
                            }

                            popup: Popup {
                                y: seedNodeCombo.height
                                width: seedNodeCombo.width
                                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: seedNodeCombo.popup.visible ? seedNodeCombo.delegateModel : null
                                    currentIndex: seedNodeCombo.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }
                            }
                        }

                        Label {
                            text: qsTr("Node that controls random seed (optional)")
                            font.pixelSize: 10
                            color: "#666666"
                        }
                    }

                    // Node count info
                    Label {
                        text: qsTr("Found ") + nodes.length + qsTr(" nodes in workflow")
                        font.pixelSize: 11
                        color: "#888888"
                    }
                }
            }
        }
    }

    onAccepted: {
        workflowName = nameField.text
        workflowType = typeCombo.currentValue || workflowType
        inputNode = getNodeIdFromCombo(inputNodeCombo)
        promptNode = getNodeIdFromCombo(promptNodeCombo)
        outputNode = getNodeIdFromCombo(outputNodeCombo)
        seedNode = getNodeIdFromCombo(seedNodeCombo)
    }
}