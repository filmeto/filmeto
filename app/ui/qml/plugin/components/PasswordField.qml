// PasswordField.qml - A password input field with show/hide toggle

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

    // Password field with toggle
    RowLayout {
        Layout.fillWidth: true
        spacing: 4

        TextField {
            id: passwordField
            Layout.fillWidth: true
            text: root.value
            placeholderText: root.placeholder
            echoMode: showPasswordButton.checked ? TextField.Normal : TextField.Password
            selectByMouse: true

            background: Rectangle {
                color: Theme.inputBackground
                border.color: passwordField.activeFocus ? Theme.borderFocus : Theme.border
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

        // Show/hide toggle button
        ToolButton {
            id: showPasswordButton
            checkable: true
            checked: false
            implicitWidth: 32
            implicitHeight: passwordField.implicitHeight

            contentItem: Text {
                text: parent.checked ? "\u{1F441}" : "\u{1F576}"  // Eye or Sunglasses emoji
                font.pixelSize: 14
                color: Theme.textSecondary
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                color: Theme.inputBackground
                border.color: Theme.border
                border.width: 1
                radius: 3
            }

            ToolTip.text: checked ? qsTr("Hide password") : qsTr("Show password")
            ToolTip.visible: hovered
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