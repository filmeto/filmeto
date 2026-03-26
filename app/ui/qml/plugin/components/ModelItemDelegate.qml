import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Rectangle {
    id: root
    property var itemData: ({})
    property color rowColor: Theme.inputBackground
    signal toggleEnabled(int displayRow, bool enabled)
    signal moveUp(int displayRow)
    signal moveDown(int displayRow)
    signal editRequested(var itemData)
    signal removeRequested(int displayRow)

    radius: 3
    color: rowColor

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 8

        Switch {
            id: rowSwitch
            checked: !!root.itemData.enabled
            onToggled: root.toggleEnabled(root.itemData.displayRow, checked)
            indicator: Rectangle {
                implicitWidth: 34
                implicitHeight: 18
                radius: height / 2
                color: rowSwitch.checked ? Theme.accent : Theme.inputBackground
                border.color: rowSwitch.checked ? Theme.borderFocus : Theme.border
                border.width: 1
                Rectangle {
                    width: 14
                    height: 14
                    radius: 7
                    y: 2
                    x: rowSwitch.checked ? parent.width - width - 2 : 2
                    color: Theme.textPrimary
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Label {
                text: root.itemData.label || ""
                color: Theme.textPrimary
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Label {
                text: (root.itemData.modelId || "") + (!!root.itemData.custom ? qsTr(" (custom)") : "")
                color: Theme.textTertiary
                font.pixelSize: 10
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Repeater {
            model: [
                { key: "up", label: qsTr("Up") },
                { key: "down", label: qsTr("Down") },
                { key: "edit", label: qsTr("Edit") }
            ]
            delegate: Button {
                text: modelData.label
                implicitHeight: 26
                onClicked: {
                    if (modelData.key === "up") root.moveUp(root.itemData.displayRow)
                    else if (modelData.key === "down") root.moveDown(root.itemData.displayRow)
                    else root.editRequested(root.itemData)
                }
                background: Rectangle {
                    color: parent.down ? Qt.darker(Theme.inputBackground, 1.15) : Theme.inputBackground
                    border.color: parent.hovered ? Theme.borderFocus : Theme.border
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: parent.text
                    color: Theme.textPrimary
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        Button {
            text: qsTr("Remove")
            implicitHeight: 26
            visible: !!root.itemData.custom
            onClicked: root.removeRequested(root.itemData.displayRow)
            background: Rectangle {
                color: parent.down ? Qt.darker(Theme.inputBackground, 1.25) : Theme.inputBackground
                border.color: parent.hovered ? Theme.borderFocus : Theme.border
                border.width: 1
                radius: 3
            }
            contentItem: Text {
                text: parent.text
                color: Theme.textPrimary
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
