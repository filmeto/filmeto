import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Rectangle {
    id: root
    property string selectedAbility: ""
    property var modelItems: []
    signal toggleEnabled(int displayRow, bool enabled)
    signal moveUp(int displayRow)
    signal moveDown(int displayRow)
    signal moveToTop(int displayRow)
    signal moveToBottom(int displayRow)
    signal editRequested(var itemData)
    signal removeRequested(int displayRow)

    color: "#1e1e1e"
    border.color: "#3a3a3a"
    radius: 4

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 6

        Label {
            text: root.selectedAbility.length ? qsTr("Models - %1").arg(root.selectedAbility) : qsTr("Models")
            font.pixelSize: 11
            font.bold: true
            color: "#b0b0b0"
        }

        ListView {
            id: modelList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.modelItems
            delegate: ModelItemDelegate {
                width: modelList.width
                height: 50
                itemData: modelData
                rowColor: index % 2 ? "#1e1e1e" : "#2d2d2d"
                onToggleEnabled: (displayRow, enabled) => root.toggleEnabled(displayRow, enabled)
                onMoveUp: displayRow => root.moveUp(displayRow)
                onMoveDown: displayRow => root.moveDown(displayRow)
                onMoveToTop: displayRow => root.moveToTop(displayRow)
                onMoveToBottom: displayRow => root.moveToBottom(displayRow)
                onEditRequested: item => root.editRequested(item)
                onRemoveRequested: displayRow => root.removeRequested(displayRow)
            }
        }
    }
}
