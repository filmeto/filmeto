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
                color: Theme.textTertiary
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Label {
                text: qsTr("Ability")
                color: Theme.textSecondary
            }
            TextField {
                id: abilityField
                Layout.fillWidth: true
                readOnly: isEdit && !editable
                placeholderText: qsTr("e.g. text2image")
                color: Theme.textPrimary
                placeholderTextColor: Theme.textTertiary
                background: Rectangle {
                    color: Theme.inputBackground
                    border.color: abilityField.activeFocus ? Theme.borderFocus : Theme.border
                    border.width: 1
                    radius: 3
                }
            }

            Label {
                text: qsTr("Model ID")
                color: Theme.textSecondary
            }
            TextField {
                id: modelIdField
                Layout.fillWidth: true
                readOnly: isEdit && !editable
                placeholderText: qsTr("model_id")
                color: Theme.textPrimary
                placeholderTextColor: Theme.textTertiary
                background: Rectangle {
                    color: Theme.inputBackground
                    border.color: modelIdField.activeFocus ? Theme.borderFocus : Theme.border
                    border.width: 1
                    radius: 3
                }
            }
        }
    }
}
