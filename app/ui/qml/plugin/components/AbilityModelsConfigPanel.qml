// Generic ability–model list: filter, sort, group, enable/disable, add/remove custom rows.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ColumnLayout {
    id: root
    property var amModel: null
    visible: amModel !== null
    Layout.fillWidth: true
    spacing: 8

    Label {
        text: "Models by ability"
        font.bold: true
        font.pixelSize: 13
        color: "#ffffff"
        Layout.fillWidth: true
    }

    Label {
        text: "Enable or disable models per ability. Custom rows can be added for IDs not in the catalog."
        font.pixelSize: 10
        color: "#808080"
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        TextField {
            id: filterField
            Layout.fillWidth: true
            implicitHeight: 30
            placeholderText: "Filter by ability, model id, or label…"
            text: amModel ? amModel.filterText : ""
            color: "#ffffff"
            placeholderTextColor: "#606060"
            verticalAlignment: TextInput.AlignVCenter
            onTextChanged: {
                if (amModel)
                    amModel.filterText = text
            }
            background: Rectangle {
                color: "#1e1e1e"
                border.color: filterField.activeFocus ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }
        }

        ComboBox {
            id: abilityFilterBox
            implicitWidth: 140
            implicitHeight: 30
            model: {
                if (!amModel)
                    return ["All abilities"]
                return ["All abilities"].concat(amModel.abilityChoices())
            }
            displayText: {
                if (currentIndex < 0)
                    return "All abilities"
                return model[currentIndex]
            }
            onActivated: function (index) {
                if (!amModel)
                    return
                if (index <= 0)
                    amModel.abilityFilter = ""
                else
                    amModel.abilityFilter = model[index]
            }
            Component.onCompleted: currentIndex = 0
            background: Rectangle {
                color: "#1e1e1e"
                border.color: abilityFilterBox.hovered ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }
            contentItem: Text {
                text: abilityFilterBox.displayText
                font.pixelSize: 11
                color: "#ffffff"
                verticalAlignment: Text.AlignVCenter
                leftPadding: 8
            }
        }

        ComboBox {
            id: sortBox
            implicitWidth: 170
            implicitHeight: 30
            model: ["Sort: ability, model", "Sort: model id"]
            currentIndex: amModel ? amModel.sortMode : 0
            onActivated: {
                if (amModel)
                    amModel.sortMode = index
            }
            background: Rectangle {
                color: "#1e1e1e"
                border.color: sortBox.hovered ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }
            contentItem: Text {
                text: sortBox.displayText
                font.pixelSize: 11
                color: "#ffffff"
                verticalAlignment: Text.AlignVCenter
                leftPadding: 8
            }
        }
    }

    CheckBox {
        id: groupBox
        text: "Group list by ability"
        contentItem: Text {
            text: groupBox.text
            font.pixelSize: 11
            color: "#cccccc"
            leftPadding: groupBox.indicator.width + groupBox.spacing
            verticalAlignment: Text.AlignVCenter
        }
        checked: amModel ? amModel.groupByAbility : true
        onToggled: {
            if (amModel)
                amModel.groupByAbility = checked
        }
        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: groupBox.leftPadding
            y: parent.height / 2 - height / 2
            radius: 3
            border.color: groupBox.checked ? "#3498db" : "#3a3a3a"
            color: groupBox.checked ? "#3498db" : "#1e1e1e"
            Text {
                visible: groupBox.checked
                text: "\u2713"
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
                anchors.centerIn: parent
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 260
        color: "#252525"
        border.color: "#3a3a3a"
        border.width: 1
        radius: 4

        ListView {
            id: listView
            anchors.fill: parent
            anchors.margins: 4
            clip: true
            model: amModel
            section.property: "section"
            section.criteria: ViewSection.FullSection
            section.labelPositioning: ViewSection.CurrentLabelAtStart
            section.delegate: Rectangle {
                width: listView.width
                height: 22
                color: "#333333"
                Label {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    leftPadding: 6
                    text: section
                    font.bold: true
                    font.pixelSize: 11
                    color: "#3498db"
                    visible: section !== ""
                }
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            delegate: Rectangle {
                width: listView.width
                height: 44
                color: index % 2 ? "#1e1e1e" : "#232323"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    spacing: 8

                    CheckBox {
                        id: rowEn
                        checked: model.enabled
                        onToggled: {
                            if (amModel)
                                amModel.setEnabledAt(index, checked)
                        }
                        indicator: Rectangle {
                            implicitWidth: 16
                            implicitHeight: 16
                            x: rowEn.leftPadding
                            y: parent.height / 2 - height / 2
                            radius: 3
                            border.color: rowEn.checked ? "#3498db" : "#3a3a3a"
                            color: rowEn.checked ? "#3498db" : "#1e1e1e"
                            Text {
                                visible: rowEn.checked
                                text: "\u2713"
                                font.pixelSize: 12
                                font.bold: true
                                color: "#ffffff"
                                anchors.centerIn: parent
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label {
                            text: model.label
                            font.pixelSize: 12
                            color: "#ffffff"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Label {
                            text: model.ability + " \u00b7 " + model.modelId + (model.custom ? " (custom)" : "")
                            font.pixelSize: 10
                            color: "#888888"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                    }

                    Button {
                        text: "Remove"
                        implicitHeight: 26
                        visible: model.custom
                        onClicked: {
                            if (amModel)
                                amModel.removeAt(index)
                        }
                        background: Rectangle {
                            color: parent.down ? "#c0392b" : "#444444"
                            radius: 3
                            border.color: "#555555"
                        }
                        contentItem: Text {
                            text: parent.text
                            color: "#ffffff"
                            font.pixelSize: 10
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 4
        Label {
            text: "Add custom model id"
            font.pixelSize: 11
            color: "#cccccc"
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            ComboBox {
                id: addAbilityBox
                implicitWidth: 140
                implicitHeight: 30
                editable: true
                model: amModel ? amModel.abilityChoices() : []
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: addAbilityBox.hovered ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }
            TextField {
                id: addModelField
                Layout.fillWidth: true
                implicitHeight: 30
                placeholderText: "model_id"
                color: "#ffffff"
                placeholderTextColor: "#606060"
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: addModelField.activeFocus ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }
            Button {
                text: "Add"
                implicitHeight: 30
                onClicked: {
                    if (!amModel || !addModelField.text)
                        return
                    var ab = addAbilityBox.editText && addAbilityBox.editText.length
                            ? addAbilityBox.editText
                            : (addAbilityBox.currentIndex >= 0 ? addAbilityBox.model[addAbilityBox.currentIndex] : "text2image")
                    amModel.addCustomEntry(ab, addModelField.text.trim())
                    addModelField.text = ""
                }
                background: Rectangle {
                    color: parent.down ? "#2980b9" : "#3498db"
                    radius: 3
                }
                contentItem: Text {
                    text: parent.text
                    color: "#ffffff"
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
