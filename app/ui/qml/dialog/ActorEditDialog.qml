import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: "transparent"
    }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            TextField {
                Layout.fillWidth: true
                placeholderText: "Character name"
                text: actorEditViewModel ? actorEditViewModel.name : ""
                enabled: actorEditViewModel ? actorEditViewModel.nameEditable : true
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_name_changed(text)
            }

            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 80
                placeholderText: "Description"
                text: actorEditViewModel ? actorEditViewModel.description : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_description_changed(text)
            }

            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: "Story"
                text: actorEditViewModel ? actorEditViewModel.story : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_story_changed(text)
            }

            Label {
                text: "Resources"
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
                    TextField {
                        Layout.fillWidth: true
                        text: modelData.path
                        readOnly: true
                    }
                    Button {
                        text: "Browse"
                        onClicked: if (actorEditViewModel) actorEditViewModel.pick_resource(modelData.key)
                    }
                    Button {
                        text: "Clear"
                        onClicked: if (actorEditViewModel) actorEditViewModel.clear_resource(modelData.key)
                    }
                }
            }

            Label {
                text: "Relationships (name: description, one per line)"
                color: "#e1e1e1"
                font.bold: true
            }
            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                text: actorEditViewModel ? actorEditViewModel.relationshipsText : ""
                onTextChanged: if (actorEditViewModel) actorEditViewModel.on_relationships_changed(text)
            }
        }
    }
}
