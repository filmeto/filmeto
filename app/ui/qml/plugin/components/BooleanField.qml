// BooleanField.qml - A checkbox for boolean configuration values

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

RowLayout {
    id: root

    property string label: ""
    property bool value: false
    property string description: ""

    signal valueChanged(bool newValue)

    spacing: 8

    // Checkbox
    CheckBox {
        id: checkBox
        checked: root.value

        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: checkBox.leftPadding
            y: parent.height / 2 - height / 2
            radius: 3
            border.color: checkBox.checked ? Theme.accent : Theme.border
            border.width: 1
            color: checkBox.checked ? Theme.accent : Theme.inputBackground

            Text {
                visible: checkBox.checked
                text: "\u2713"  // Checkmark
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
                anchors.centerIn: parent
            }
        }

        onCheckedChanged: {
            if (checked !== root.value) {
                root.valueChanged(checked)
            }
        }
    }

    // Label and description
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Label {
            text: root.label
            font.pixelSize: 12
            color: Theme.textLabel
            Layout.fillWidth: true

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: checkBox.checked = !checkBox.checked
            }
        }

        Label {
            visible: root.description !== ""
            text: root.description
            font.pixelSize: 10
            color: Theme.textTertiary
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}