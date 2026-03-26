import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Rectangle {
    id: root
    property var abilityItems: []
    property string selectedAbility: ""
    signal abilitySelected(string ability)

    color: Theme.inputBackground
    border.color: Theme.border
    radius: 4

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 6

        Label {
            text: qsTr("Abilities")
            font.pixelSize: 11
            font.bold: true
            color: Theme.textSecondary
        }

        ListView {
            id: abilityList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.abilityItems
            delegate: Rectangle {
                width: abilityList.width
                height: 34
                color: modelData.ability === root.selectedAbility ? Qt.lighter(Theme.accent, 0.55) : (index % 2 ? Theme.inputBackground : Theme.cardBackground)
                radius: 3

                MouseArea {
                    anchors.fill: parent
                    onClicked: root.abilitySelected(modelData.ability)
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 4

                    Label {
                        Layout.fillWidth: true
                        text: modelData.ability
                        color: Theme.textPrimary
                        elide: Text.ElideRight
                    }
                    Label {
                        text: modelData.enabled + "/" + modelData.total
                        color: Theme.textTertiary
                        font.pixelSize: 10
                    }
                }
            }
        }
    }
}
