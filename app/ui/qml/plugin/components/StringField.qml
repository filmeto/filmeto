// StringField.qml - A text input field for string configuration values

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root

    property string label: ""
    property string value: ""
    property string placeholder: ""
    property string description: ""
    property bool required: false
    property bool readOnly: false

    signal valueChanged(string newValue)

    spacing: 4

    // Label
    Label {
        text: root.label + (root.required ? " *" : "")
        font.pixelSize: 12
        color: Theme.textLabel
        Layout.fillWidth: true

        ToolTip.visible: root.description !== "" && ma_label.containsMouse
        ToolTip.text: root.description
        ToolTip.delay: 500

        MouseArea {
            id: ma_label
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }
    }

    // Text field
    TextField {
        id: textField
        Layout.fillWidth: true
        text: root.value
        placeholderText: root.placeholder
        readOnly: root.readOnly
        selectByMouse: true

        background: Rectangle {
            color: Theme.inputBackground
            border.color: textField.activeFocus ? Theme.borderFocus : Theme.border
            border.width: 1
            radius: 3
        }

        color: Theme.textPrimary
        placeholderTextColor: Theme.textTertiary
        selectionColor: Theme.accent
        selectedTextColor: "#ffffff"

        onTextChanged: {
            if (text !== root.value) {
                root.valueChanged(text)
            }
        }
    }

    // Description text (optional)
    Label {
        visible: root.description !== ""
        text: root.description
        font.pixelSize: 10
        color: Theme.textTertiary
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
}