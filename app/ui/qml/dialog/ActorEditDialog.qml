import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common/buttons" as CommonButtons
import "../common/inputs" as CommonInputs

Item {
    id: root
    anchors.fill: parent

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            CommonInputs.TextInput {
                Layout.fillWidth: true
                placeholderText: qsTr("Character name")
                text: actorEditViewModel ? actorEditViewModel.name : ""
                enabled: actorEditViewModel ? actorEditViewModel.nameEditable : true
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_name_changed(text)
            }

            CommonInputs.TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                placeholderText: qsTr("Description")
                text: actorEditViewModel ? actorEditViewModel.description : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_description_changed(text)
            }

            CommonInputs.TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: qsTr("Story")
                text: actorEditViewModel ? actorEditViewModel.story : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_story_changed(text)
            }

            Label {
                text: qsTr("Resources")
                color: "#e1e1e1"
                font.bold: true
            }

            Repeater {
                model: actorEditViewModel ? actorEditViewModel.resourceItems : []
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: modelData.label
                        color: "#e1e1e1"
                        Layout.preferredWidth: 90
                    }
                    CommonInputs.TextInput {
                        Layout.fillWidth: true
                        text: modelData.path
                        readOnly: true
                    }
                    CommonButtons.SecondaryButton {
                        text: qsTr("Browse")
                        size: "small"
                        onClicked: if (actorEditViewModel) actorEditViewModel.pick_resource(modelData.key)
                    }
                    CommonButtons.GhostButton {
                        text: qsTr("Clear")
                        size: "small"
                        onClicked: if (actorEditViewModel) actorEditViewModel.clear_resource(modelData.key)
                    }
                }
            }

            Label {
                text: qsTr("Relationships (name: description, one per line)")
                color: "#e1e1e1"
                font.bold: true
            }
            CommonInputs.TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                text: actorEditViewModel ? actorEditViewModel.relationshipsText : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_relationships_changed(text)
            }
        }
    }
}
