// ModelsTab.qml - Models Configuration Tab
// Reuses AbilityModelsConfigPanel for ability-model configuration

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var configModel: null

    AbilityModelsConfigPanel {
        anchors.fill: parent
        anchors.margins: 16
        amModel: configModel ? configModel.abilityModelsModel : null
    }
}