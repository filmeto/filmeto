// Ability -> models cascaded editor with toolbar, filters and modal add/edit.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0
import "../../dialog"

ColumnLayout {
    id: root
    property var amModel: null
    property string selectedAbility: ""
    property bool showFilters: false
    property var abilityItems: []
    property var modelItems: []
    property int editingDisplayRow: -1
    property bool editingCustom: false
    readonly property color bg: Theme.backgroundColor
    readonly property color panelBg: Theme.cardBackground
    readonly property color inputBg: Theme.inputBackground
    readonly property color border: Theme.border
    readonly property color borderFocus: Theme.borderFocus
    readonly property color textPrimary: Theme.textPrimary
    readonly property color textSecondary: Theme.textSecondary
    readonly property color textMuted: Theme.textTertiary
    readonly property color accent: Theme.accent
    readonly property color onAccentText: Theme.textPrimary
    visible: amModel !== null
    Layout.fillWidth: true
    spacing: 8

    Label {
        text: qsTr("Models by ability")
        font.bold: true
        font.pixelSize: 13
        color: textPrimary
        Layout.fillWidth: true
    }

    Label {
        text: qsTr("Manage models by ability with clear filters, ordering and quick actions.")
        font.pixelSize: 10
        color: textMuted
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: filterField
                Layout.fillWidth: true
                implicitHeight: 30
                placeholderText: qsTr("Search ability/model...")
                text: amModel ? amModel.filterText : ""
                color: textPrimary
                placeholderTextColor: textMuted
                verticalAlignment: TextInput.AlignVCenter
                onTextChanged: {
                    if (amModel) {
                        amModel.filterText = text
                        root.refreshData()
                    }
                }
                background: Rectangle {
                    color: inputBg
                    border.color: filterField.activeFocus ? borderFocus : border
                    border.width: 1
                    radius: 3
                }
            }

            Button {
                id: filterButton
                text: showFilters ? qsTr("Hide Filters") : qsTr("Filters")
                implicitHeight: 30
                onClicked: showFilters = !showFilters
                background: Rectangle {
                    color: filterButton.down ? Qt.darker(inputBg, 1.15) : inputBg
                    border.color: filterButton.hovered ? borderFocus : border
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: filterButton.text
                    font.pixelSize: 11
                    color: textPrimary
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        Button {
            id: addButton
            text: qsTr("Add")
            implicitHeight: 30
            onClicked: {
                addAbilityField.text = selectedAbility.length ? selectedAbility : "text2image"
                addModelField.text = ""
                addDialog.open()
            }
            background: Rectangle {
                color: addButton.down ? Qt.darker(accent, 1.2) : accent
                radius: 3
            }
            contentItem: Text {
                text: addButton.text
                color: onAccentText
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        visible: showFilters
        color: panelBg
        border.color: border
        radius: 4
        implicitHeight: filterRow.implicitHeight + 14

        RowLayout {
            id: filterRow
            anchors.fill: parent
            anchors.margins: 7
            spacing: 12

            ComboBox {
                id: sortBox
                implicitWidth: 170
                implicitHeight: 28
                model: [qsTr("Sort: ability, model"), qsTr("Sort: model id"), qsTr("Sort: custom order")]
                currentIndex: amModel ? amModel.sortMode : 2
                onActivated: {
                    if (amModel) {
                        amModel.sortMode = index
                        root.refreshData()
                    }
                }
                background: Rectangle {
                    color: inputBg
                    border.color: sortBox.hovered ? borderFocus : border
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: sortBox.displayText
                    color: textPrimary
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
            }

            CheckBox {
                id: enabledOnlyBox
                text: qsTr("Enabled only")
                checked: amModel ? amModel.enabledOnly : false
                onToggled: {
                    if (amModel) {
                        amModel.enabledOnly = checked
                        root.refreshData()
                    }
                }
                contentItem: Text {
                    text: enabledOnlyBox.text
                    color: textSecondary
                    leftPadding: enabledOnlyBox.indicator.width + enabledOnlyBox.spacing
                    verticalAlignment: Text.AlignVCenter
                }
                indicator: Rectangle {
                    implicitWidth: 16
                    implicitHeight: 16
                    x: enabledOnlyBox.leftPadding
                    y: parent.height / 2 - height / 2
                    radius: 3
                    border.color: enabledOnlyBox.checked ? borderFocus : border
                    color: enabledOnlyBox.checked ? accent : inputBg
                }
            }

            CheckBox {
                id: customOnlyBox
                text: qsTr("Custom only")
                checked: amModel ? amModel.customOnly : false
                onToggled: {
                    if (amModel) {
                        amModel.customOnly = checked
                        root.refreshData()
                    }
                }
                contentItem: Text {
                    text: customOnlyBox.text
                    color: textSecondary
                    leftPadding: customOnlyBox.indicator.width + customOnlyBox.spacing
                    verticalAlignment: Text.AlignVCenter
                }
                indicator: Rectangle {
                    implicitWidth: 16
                    implicitHeight: 16
                    x: customOnlyBox.leftPadding
                    y: parent.height / 2 - height / 2
                    radius: 3
                    border.color: customOnlyBox.checked ? borderFocus : border
                    color: customOnlyBox.checked ? accent : inputBg
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 340
        color: panelBg
        border.color: border
        border.width: 1
        radius: 4

        RowLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                color: inputBg
                border.color: border
                radius: 4

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 6

                    Label {
                        text: qsTr("Abilities")
                        font.pixelSize: 11
                        font.bold: true
                        color: textSecondary
                    }

                    ListView {
                        id: abilityList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: abilityItems
                        delegate: Rectangle {
                            width: abilityList.width
                            height: 34
                            color: modelData.ability === selectedAbility ? Qt.lighter(accent, 0.55) : (index % 2 ? inputBg : panelBg)
                            radius: 3

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    selectedAbility = modelData.ability
                                    if (amModel)
                                        amModel.abilityFilter = selectedAbility
                                    root.refreshData()
                                }
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 4
                                Label {
                                    Layout.fillWidth: true
                                    text: modelData.ability
                                    color: textPrimary
                                    elide: Text.ElideRight
                                }
                                Label {
                                    text: modelData.enabled + "/" + modelData.total
                                    color: textMuted
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: inputBg
                border.color: border
                radius: 4

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: 6

                    Label {
                        text: selectedAbility.length ? qsTr("Models - %1").arg(selectedAbility) : qsTr("Models")
                        font.pixelSize: 11
                        font.bold: true
                        color: textSecondary
                    }

                    ListView {
                        id: modelList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: modelItems
                        delegate: Rectangle {
                            width: modelList.width
                            height: 50
                            color: index % 2 ? inputBg : panelBg
                            radius: 3

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                Switch {
                                    id: rowSwitch
                                    checked: !!modelData.enabled
                                    onToggled: {
                                        if (amModel)
                                            amModel.setEnabledAt(modelData.displayRow, checked)
                                        root.refreshData()
                                    }
                                    indicator: Rectangle {
                                        implicitWidth: 34
                                        implicitHeight: 18
                                        radius: height / 2
                                        color: rowSwitch.checked ? accent : inputBg
                                        border.color: rowSwitch.checked ? borderFocus : border
                                        border.width: 1
                                        Rectangle {
                                            width: 14
                                            height: 14
                                            radius: 7
                                            y: 2
                                            x: rowSwitch.checked ? parent.width - width - 2 : 2
                                            color: textPrimary
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Label {
                                        text: modelData.label
                                        color: textPrimary
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                    Label {
                                        text: modelData.modelId + (modelData.custom ? qsTr(" (custom)") : "")
                                        color: textMuted
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                        Layout.fillWidth: true
                                    }
                                }

                                Button {
                                    text: qsTr("Up")
                                    implicitHeight: 26
                                    onClicked: {
                                        if (amModel)
                                            amModel.moveAt(modelData.displayRow, -1)
                                        root.refreshData()
                                    }
                                    background: Rectangle {
                                        color: parent.down ? Qt.darker(inputBg, 1.15) : inputBg
                                        border.color: parent.hovered ? borderFocus : border
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: textPrimary
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }

                                Button {
                                    text: qsTr("Down")
                                    implicitHeight: 26
                                    onClicked: {
                                        if (amModel)
                                            amModel.moveAt(modelData.displayRow, 1)
                                        root.refreshData()
                                    }
                                    background: Rectangle {
                                        color: parent.down ? Qt.darker(inputBg, 1.15) : inputBg
                                        border.color: parent.hovered ? borderFocus : border
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: textPrimary
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }

                                Button {
                                    text: qsTr("Edit")
                                    implicitHeight: 26
                                    onClicked: {
                                        editingDisplayRow = modelData.displayRow
                                        editingCustom = !!modelData.custom
                                        editAbilityField.text = modelData.ability
                                        editModelField.text = modelData.modelId
                                        editDialog.open()
                                    }
                                    background: Rectangle {
                                        color: parent.down ? Qt.darker(inputBg, 1.15) : inputBg
                                        border.color: parent.hovered ? borderFocus : border
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: textPrimary
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }

                                Button {
                                    text: qsTr("Remove")
                                    implicitHeight: 26
                                    visible: !!modelData.custom
                                    onClicked: {
                                        if (amModel)
                                            amModel.removeAt(modelData.displayRow)
                                        root.refreshData()
                                    }
                                    background: Rectangle {
                                        color: parent.down ? Qt.darker(inputBg, 1.25) : inputBg
                                        border.color: parent.hovered ? borderFocus : border
                                        border.width: 1
                                        radius: 3
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: textPrimary
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function refreshData() {
        if (!amModel) {
            abilityItems = []
            modelItems = []
            selectedAbility = ""
            return
        }

        abilityItems = amModel.abilityStats()
        if (!selectedAbility.length && abilityItems.length > 0)
            selectedAbility = abilityItems[0].ability

        var exists = false
        for (var i = 0; i < abilityItems.length; ++i) {
            if (abilityItems[i].ability === selectedAbility) {
                exists = true
                break
            }
        }
        if (!exists)
            selectedAbility = abilityItems.length > 0 ? abilityItems[0].ability : ""

        if (selectedAbility.length)
            amModel.abilityFilter = selectedAbility
        else
            amModel.abilityFilter = ""
        modelItems = amModel.modelsForAbility(selectedAbility)
    }

    Component.onCompleted: refreshData()

    Connections {
        target: amModel
        function onPersisted() { root.refreshData() }
        function onFilterTextChanged() { root.refreshData() }
        function onAbilityFilterChanged() { root.refreshData() }
        function onSortModeChanged() { root.refreshData() }
        function onEnabledOnlyChanged() { root.refreshData() }
        function onCustomOnlyChanged() { root.refreshData() }
    }

    CustomDialog {
        id: addDialog
        title: qsTr("Add model")
        dialogWidth: 420

        onAccepted: {
            if (!amModel)
                return
            amModel.addCustomEntry(addAbilityField.text, addModelField.text)
            selectedAbility = addAbilityField.text
            root.refreshData()
        }

        content: Component {
            ColumnLayout {
                spacing: 12
                Label {
                    text: qsTr("Ability")
                    color: textSecondary
                }
                TextField {
                    id: addAbilityField
                    Layout.fillWidth: true
                    placeholderText: qsTr("e.g. text2image")
                    color: textPrimary
                    placeholderTextColor: textMuted
                    background: Rectangle {
                        color: inputBg
                        border.color: addAbilityField.activeFocus ? borderFocus : border
                        border.width: 1
                        radius: 3
                    }
                }
                Label {
                    text: qsTr("Model ID")
                    color: textSecondary
                }
                TextField {
                    id: addModelField
                    Layout.fillWidth: true
                    placeholderText: qsTr("model_id")
                    color: textPrimary
                    placeholderTextColor: textMuted
                    background: Rectangle {
                        color: inputBg
                        border.color: addModelField.activeFocus ? borderFocus : border
                        border.width: 1
                        radius: 3
                    }
                }
            }
        }
    }

    CustomDialog {
        id: editDialog
        title: qsTr("Edit model")
        dialogWidth: 420

        onAccepted: {
            if (!amModel || editingDisplayRow < 0)
                return
            amModel.updateEntryAt(editingDisplayRow, editAbilityField.text, editModelField.text)
            selectedAbility = editAbilityField.text
            root.refreshData()
        }

        content: Component {
            ColumnLayout {
                spacing: 12
                Label {
                    visible: !editingCustom
                    text: qsTr("Built-in model can only be viewed, not renamed.")
                    color: textMuted
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
                Label {
                    text: qsTr("Ability")
                    color: textSecondary
                }
                TextField {
                    id: editAbilityField
                    Layout.fillWidth: true
                    readOnly: !editingCustom
                    color: textPrimary
                    placeholderTextColor: textMuted
                    background: Rectangle {
                        color: inputBg
                        border.color: editAbilityField.activeFocus ? borderFocus : border
                        border.width: 1
                        radius: 3
                    }
                }
                Label {
                    text: qsTr("Model ID")
                    color: textSecondary
                }
                TextField {
                    id: editModelField
                    Layout.fillWidth: true
                    readOnly: !editingCustom
                    color: textPrimary
                    placeholderTextColor: textMuted
                    background: Rectangle {
                        color: inputBg
                        border.color: editModelField.activeFocus ? borderFocus : border
                        border.width: 1
                        radius: 3
                    }
                }
            }
        }
    }
}
