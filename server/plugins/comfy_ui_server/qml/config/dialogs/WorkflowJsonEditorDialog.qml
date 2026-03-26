// WorkflowJsonEditorDialog.qml - Dialog for editing workflow JSON content
// Provides a text editor with JSON validation

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: root

    // Properties to be set before opening
    property string workflowType: ""
    property string jsonContent: ""

    // Result
    property string savedContent: ""

    title: qsTr("Edit Workflow JSON")
    modal: true
    standardButtons: Dialog.Cancel | Dialog.Save

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

        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 6
            color: parent.color
        }

        Label {
            text: root.title + ": " + workflowType
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
            id: saveButton
            text: qsTr("Save")
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            enabled: isValidJson

            background: Rectangle {
                implicitHeight: 32
                color: parent.enabled ? (parent.hovered ? "#5dade2" : "#3498db") : "#555555"
                radius: 4
            }

            contentItem: Text {
                text: parent.text
                font.pixelSize: 12
                font.bold: true
                color: parent.enabled ? "#ffffff" : "#888888"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    property bool isValidJson: false

    function validateJson(text) {
        if (!text || text.trim() === "") {
            statusText.text = qsTr("JSON content cannot be empty")
            statusText.color = "#e74c3c"
            return false
        }

        try {
            JSON.parse(text)
            statusText.text = qsTr("Valid JSON format")
            statusText.color = "#27ae60"
            return true
        } catch (e) {
            statusText.text = qsTr("Invalid JSON: ") + e.message
            statusText.color = "#e74c3c"
            return false
        }
    }

    function formatJson(text) {
        try {
            var obj = JSON.parse(text)
            return JSON.stringify(obj, null, 2)
        } catch (e) {
            return text
        }
    }

    contentItem: ColumnLayout {
        spacing: 10

        // Info label
        Label {
            text: qsTr("Edit the JSON content below. Make sure it's valid JSON format.")
            font.pixelSize: 11
            color: "#888888"
            Layout.fillWidth: true
        }

        // JSON Editor
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e"
            border.color: jsonEditor.activeFocus ? "#3498db" : "#3a3a3a"
            border.width: 1
            radius: 4

            ScrollView {
                anchors.fill: parent
                anchors.margins: 4
                clip: true

                TextArea {
                    id: jsonEditor
                    text: jsonContent
                    selectByMouse: true
                    wrapMode: TextArea.NoWrap
                    font.family: "Courier New, Monaco, Consolas, monospace"
                    font.pixelSize: 12
                    color: "#ffffff"
                    selectionColor: "#3498db"
                    selectedTextColor: "#ffffff"

                    background: null

                    onTextChanged: {
                        isValidJson = validateJson(text)
                    }
                }
            }
        }

        // Status label
        Label {
            id: statusText
            text: qsTr("Valid JSON format")
            font.pixelSize: 10
            color: "#27ae60"
            Layout.fillWidth: true
        }

        // Format button
        Button {
            text: qsTr("Format JSON")
            implicitHeight: 28
            Layout.alignment: Qt.AlignRight

            background: Rectangle {
                color: parent.hovered ? "#555555" : "#444444"
                radius: 4
            }

            contentItem: Text {
                text: parent.text
                font.pixelSize: 11
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            onClicked: {
                jsonEditor.text = formatJson(jsonEditor.text)
            }
        }
    }

    onOpened: {
        jsonEditor.text = jsonContent
        isValidJson = validateJson(jsonContent)
    }

    onAccepted: {
        savedContent = jsonEditor.text
    }
}