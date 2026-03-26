// Embeds AbilityModelsConfigPanel with `abilityModelsConfigModel` from engine context (Python QQuickWidget).
import QtQuick 2.15
import plugin 1.0

AbilityModelsConfigPanel {
    anchors.fill: parent
    amModel: typeof abilityModelsConfigModel !== "undefined" ? abilityModelsConfigModel : null
}
