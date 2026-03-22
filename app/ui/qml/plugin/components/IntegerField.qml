// IntegerField.qml - A spinbox for integer configuration values

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

ColumnLayout {
    id: root

    property string label: ""
    property int value: 0
    property int minValue: -2147483648
    property int maxValue: 2147483647
    property int stepSize: 1
    property string description: ""
    property bool required: false

    signal valueChanged(int newValue)

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

    // SpinBox
    SpinBox {
        id: spinBox
        Layout.fillWidth: true
        value: root.value
        from: root.minValue
        to: root.maxValue
        stepSize: root.stepSize
        editable: true

        background: Rectangle {
            color: Theme.inputBackground
            border.color: spinBox.activeFocus ? Theme.borderFocus : Theme.border
            border.width: 1
            radius: 3
        }

        contentItem: TextInput {
            text: spinBox.textFromValue(spinBox.value, spinBox.locale)
            font.pixelSize: 12
            color: Theme.textPrimary
            selectionColor: Theme.accent
            selectedTextColor: "#ffffff"
            horizontalAlignment: Qt.AlignHCenter
            verticalAlignment: Qt.AlignVCenter
            readOnly: !spinBox.editable
            validator: spinBox.validator
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }

        up.indicator: Rectangle {
            x: spinBox.mirrored ? 0 : parent.width - width
            height: parent.height
            implicitWidth: 30
            implicitHeight: 30
            color: up.pressed ? Theme.accentHover : Theme.cardBackground
            border.color: Theme.border
            border.width: 1
            radius: 3

            Text {
                text: "+"
                font.pixelSize: 14
                font.bold: true
                color: Theme.textPrimary
                anchors.centerIn: parent
            }
        }

        down.indicator: Rectangle {
            x: spinBox.mirrored ? parent.width - width : 0
            height: parent.height
            implicitWidth: 30
            implicitHeight: 30
            color: down.pressed ? Theme.accentHover : Theme.cardBackground
            border.color: Theme.border
            border.width: 1
            radius: 3

            Text {
                text: "-"
                font.pixelSize: 14
                font.bold: true
                color: Theme.textPrimary
                anchors.centerIn: parent
            }
        }

        onValueChanged: {
            if (value !== root.value) {
                root.valueChanged(value)
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