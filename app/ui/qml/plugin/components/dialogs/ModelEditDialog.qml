import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Dialog {
    id: root
    property bool isEdit: false
    property bool editable: true
    property string abilityValue: ""
    property string modelIdValue: ""
    signal submitted(string ability, string modelId)

    modal: true
    width: 420
    title: isEdit ? qsTr("Edit model") : qsTr("Add model")
    standardButtons: Dialog.Ok | Dialog.Cancel

    // Center the dialog on the parent
    x: (parent ? parent.width / 2 - width / 2 : 0)
    y: (parent ? parent.height / 2 - height / 2 : 0)

    background: Rectangle {
        color: "#2d2d2d"
        border.color: "#3a3a3a"
        radius: 4
    }

    header: Rectangle {
        color: "#2d2d2d"
        implicitHeight: 36
        Text {
            anchors.centerIn: parent
            text: root.title
            color: "#e0e0e0"
            font.bold: true
            font.pixelSize: 13
        }
    }

    footer: DialogButtonBox {
        background: Rectangle { color: "#2d2d2d" }
        buttonLayout: DialogButtonBox.LinearLayout
        delegate: Button {
            background: Rectangle {
                color: parent.down ? "#252525" : "#1e1e1e"
                border.color: parent.hovered ? "#3498db" : "#3a3a3a"
                radius: 3
            }
            contentItem: Text {
                text: parent.text
                color: "#e0e0e0"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    onOpened: {
        abilityField.text = abilityValue
        modelIdField.text = modelIdValue
    }

    onAccepted: submitted(abilityField.text, modelIdField.text)

    contentItem: Item {
        implicitWidth: 396
        implicitHeight: isEdit ? 154 : 126
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Label {
                visible: isEdit && !editable
                text: qsTr("Built-in model can only be viewed, not renamed.")
                color: "#808080"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: qsTr("Ability")
                color: "#b0b0b0"
            }
            TextField {
                id: abilityField
                Layout.fillWidth: true
                readOnly: isEdit && !editable
                placeholderText: qsTr("e.g. text2image")
                color: "#e0e0e0"
                placeholderTextColor: "#808080"
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: abilityField.activeFocus ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }

            Label {
                text: qsTr("Model ID")
                color: "#b0b0b0"
            }
            TextField {
                id: modelIdField
                Layout.fillWidth: true
                readOnly: isEdit && !editable
                placeholderText: qsTr("model_id")
                color: "#e0e0e0"
                placeholderTextColor: "#808080"
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: modelIdField.activeFocus ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }
        }
    }
}