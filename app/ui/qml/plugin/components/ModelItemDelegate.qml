import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Rectangle {
    id: root
    property var itemData: ({})
    property color rowColor: "#1e1e1e"
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
                color: rowSwitch.checked ? "#3498db" : "#1e1e1e"
                border.color: rowSwitch.checked ? "#3498db" : "#3a3a3a"
                border.width: 1
                Rectangle {
                    width: 14
                    height: 14
                    radius: 7
                    y: 2
                    x: rowSwitch.checked ? parent.width - width - 2 : 2
                    color: "#e0e0e0"
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Label {
                text: root.itemData.label || ""
                color: "#e0e0e0"
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
            Label {
                text: (root.itemData.modelId || "") + (!!root.itemData.custom ? qsTr(" (custom)") : "")
                color: "#808080"
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
                    color: parent.down ? "#252525" : "#1e1e1e"
                    border.color: parent.hovered ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: parent.text
                    color: "#e0e0e0"
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
                color: parent.down ? "#2a1a1a" : "#1e1e1e"
                border.color: parent.hovered ? "#e74c3c" : "#3a3a3a"
                border.width: 1
                radius: 3
            }
            contentItem: Text {
                text: parent.text
                color: "#e0e0e0"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}