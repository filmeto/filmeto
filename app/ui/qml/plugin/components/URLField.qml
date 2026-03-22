// URLField.qml - A text input field optimized for URL configuration values

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root

    property string label: ""
    property string value: ""
    property string placeholder: "https://"
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

    // URL field with validation indicator
    RowLayout {
        Layout.fillWidth: true
        spacing: 4

        TextField {
            id: urlField
            Layout.fillWidth: true
            text: root.value
            placeholderText: root.placeholder
            selectByMouse: true

            // Basic URL validation
            property bool isValidUrl: text === "" || text.match(/^https?:\/\/.+/)

            background: Rectangle {
                color: Theme.inputBackground
                border.color: urlField.activeFocus ? Theme.borderFocus :
                              (urlField.isValidUrl ? Theme.border : Theme.borderError)
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

        // Validation indicator
        Rectangle {
            visible: urlField.text !== ""
            width: 8
            height: 8
            radius: 4
            color: urlField.isValidUrl ? Theme.statusSuccess : Theme.statusError

            ToolTip.text: urlField.isValidUrl ? qsTr("Valid URL") : qsTr("Invalid URL format")
            ToolTip.visible: ma_indicator.containsMouse
            ToolTip.delay: 500

            MouseArea {
                id: ma_indicator
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
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