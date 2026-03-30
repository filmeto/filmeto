import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0
import "dialogs" as Dialogs

ColumnLayout {
    id: root
    property var amModel: null
    property string selectedAbility: ""
    property bool showFilters: false
    property var abilityItems: []
    property var modelItems: []
    property int editingDisplayRow: -1
    property bool editingCustom: false
    visible: amModel !== null
    Layout.fillWidth: true
    spacing: 8

    Label {
        text: qsTr("Models by ability")
        font.bold: true
        font.pixelSize: 13
        color: "#e0e0e0"
        Layout.fillWidth: true
    }

    Label {
        text: qsTr("Manage models by ability with clear filters, ordering and quick actions.")
        font.pixelSize: 10
        color: "#808080"
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    AbilityModelsToolbar {
        Layout.fillWidth: true
        filterText: amModel ? amModel.filterText : ""
        showFilters: root.showFilters
        sortMode: amModel ? amModel.sortMode : 2
        enabledOnly: amModel ? amModel.enabledOnly : false
        customOnly: amModel ? amModel.customOnly : false
        defaultAbility: root.selectedAbility.length ? root.selectedAbility : "text2image"
        onFilterTextEdited: text => {
            if (!amModel) return
            amModel.filterText = text
            root.refreshData()
        }
        onToggleFilters: root.showFilters = !root.showFilters
        onAddClicked: ability => {
            addDialog.abilityValue = ability
            addDialog.modelIdValue = ""
            addDialog.open()
        }
        onSortModeSelected: mode => {
            if (!amModel) return
            amModel.sortMode = mode
            root.refreshData()
        }
        onEnabledOnlyToggled: checked => {
            if (!amModel) return
            amModel.enabledOnly = checked
            root.refreshData()
        }
        onCustomOnlyToggled: checked => {
            if (!amModel) return
            amModel.customOnly = checked
            root.refreshData()
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 340
        color: "#2d2d2d"
        border.color: "#3a3a3a"
        border.width: 1
        radius: 4

        RowLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 8

            AbilityListPanel {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                abilityItems: root.abilityItems
                selectedAbility: root.selectedAbility
                onAbilitySelected: ability => {
                    root.selectedAbility = ability
                    if (amModel) amModel.abilityFilter = root.selectedAbility
                    root.refreshData()
                }
            }

            ModelListPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                selectedAbility: root.selectedAbility
                modelItems: root.modelItems
                onToggleEnabled: (displayRow, enabled) => {
                    if (!amModel) return
                    amModel.setEnabledAt(displayRow, enabled)
                    root.refreshData()
                }
                onMoveUp: displayRow => {
                    if (!amModel) return
                    amModel.moveAt(displayRow, -1)
                    root.refreshData()
                }
                onMoveDown: displayRow => {
                    if (!amModel) return
                    amModel.moveAt(displayRow, 1)
                    root.refreshData()
                }
                onMoveToTop: displayRow => {
                    if (!amModel) return
                    amModel.moveToTop(displayRow)
                    root.refreshData()
                }
                onMoveToBottom: displayRow => {
                    if (!amModel) return
                    amModel.moveToBottom(displayRow)
                    root.refreshData()
                }
                onEditRequested: itemData => {
                    root.editingDisplayRow = itemData.displayRow
                    root.editingCustom = !!itemData.custom
                    editDialog.abilityValue = itemData.ability
                    editDialog.modelIdValue = itemData.modelId
                    editDialog.editable = root.editingCustom
                    editDialog.open()
                }
                onRemoveRequested: displayRow => {
                    if (!amModel) return
                    amModel.removeAt(displayRow)
                    root.refreshData()
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

        amModel.abilityFilter = selectedAbility.length ? selectedAbility : ""
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

    Dialogs.ModelEditDialog {
        id: addDialog
        isEdit: false
        editable: true
        onSubmitted: (ability, modelId) => {
            if (!amModel) return
            amModel.addCustomEntry(ability, modelId)
            root.selectedAbility = ability
            root.refreshData()
        }
    }

    Dialogs.ModelEditDialog {
        id: editDialog
        isEdit: true
        editable: root.editingCustom
        onSubmitted: (ability, modelId) => {
            if (!amModel || root.editingDisplayRow < 0) return
            amModel.updateEntryAt(root.editingDisplayRow, ability, modelId)
            root.selectedAbility = ability
            root.refreshData()
        }
    }
}
