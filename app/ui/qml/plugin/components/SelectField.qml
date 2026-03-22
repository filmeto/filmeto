// SelectField.qml - A dropdown/combobox for selecting from predefined options

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root

    property string label: ""
    property string value: ""
    property var options: []  // Array of strings or {value, text} objects
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

    // ComboBox
    ComboBox {
        id: comboBox
        Layout.fillWidth: true

        // Build model from options
        model: root.options.map(function(opt) {
            return typeof opt === 'object' ? opt.text : opt
        })

        property var valueModel: root.options.map(function(opt) {
            return typeof opt === 'object' ? opt.value : opt
        })

        // Set initial index based on value
        Component.onCompleted: {
            var idx = valueModel.indexOf(root.value)
            if (idx >= 0) {
                currentIndex = idx
            }
        }

        // Update when value changes externally
        onValueChanged: {
            var idx = valueModel.indexOf(root.value)
            if (idx >= 0 && idx !== currentIndex) {
                currentIndex = idx
            }
        }

        background: Rectangle {
            color: Theme.inputBackground
            border.color: comboBox.popup.visible ? Theme.borderFocus :
                          (comboBox.hovered ? Theme.accent : Theme.border)
            border.width: 1
            radius: 3
            implicitHeight: 30
        }

        contentItem: Text {
            text: comboBox.displayText
            font.pixelSize: 12
            color: Theme.textPrimary
            verticalAlignment: Text.AlignVCenter
            leftPadding: 10
            rightPadding: comboBox.indicator.width + 10
            elide: Text.ElideRight
        }

        indicator: Text {
            x: comboBox.width - width - 10
            y: (comboBox.height - height) / 2
            text: "\u25BC"  // Down arrow
            font.pixelSize: 10
            color: Theme.textSecondary
        }

        delegate: ItemDelegate {
            width: comboBox.width
            height: 30

            contentItem: Text {
                text: modelData
                font.pixelSize: 12
                color: Theme.textPrimary
                verticalAlignment: Text.AlignVCenter
                leftPadding: 10
            }

            background: Rectangle {
                color: highlighted ? Theme.accent : (hovered ? Theme.cardBackground : Theme.inputBackground)
            }

            highlighted: comboBox.highlightedIndex === index
        }

        popup: Popup {
            y: comboBox.height
            width: comboBox.width
            implicitHeight: contentItem.implicitHeight
            padding: 1

            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: comboBox.popup.visible ? comboBox.delegateModel : null
                currentIndex: comboBox.highlightedIndex
            }

            background: Rectangle {
                color: Theme.inputBackground
                border.color: Theme.border
                radius: 3
            }
        }

        onCurrentIndexChanged: {
            if (currentIndex >= 0 && currentIndex < valueModel.length) {
                var newValue = valueModel[currentIndex]
                if (newValue !== root.value) {
                    root.valueChanged(newValue)
                }
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