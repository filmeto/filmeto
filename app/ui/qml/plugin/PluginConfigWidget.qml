// PluginConfigWidget.qml - Root container for plugin configuration UI
// Automatically renders fields from config_schema if no custom QML is provided

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // Configuration model reference (set from Python)
    // Expected properties/methods:
    // - plugin_name: string
    // - config_schema: object
    // - get_config_value(key): returns value
    // - set_config_value(key, value): sets value
    // - get_config_dict(): returns all config as dict
    // - validate(): returns bool
    property var configModel: null

    // Exposed methods for external access
    function getConfig() {
        if (configModel && typeof configModel.get_config_dict === 'function') {
            return configModel.get_config_dict()
        }
        return {}
    }

    function validate() {
        if (configModel && typeof configModel.validate === 'function') {
            return configModel.validate()
        }
        return true
    }

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ScrollView {
        anchors.fill: parent
        clip: true

        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Flickable {
            id: flickable
            contentWidth: flickable.width
            contentHeight: mainLayout.implicitHeight + 32

            ColumnLayout {
                id: mainLayout
                width: Math.max(flickable.width - 32, 400)
                x: 16
                y: 16
                spacing: 16

                // Plugin header
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: configModel ? configModel.plugin_name : "Plugin Configuration"
                        font.bold: true
                        font.pixelSize: 16
                        color: "#e0e0e0"
                        Layout.fillWidth: true
                    }

                    // Separator line
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: "#3a3a3a"
                    }
                }

                // Fields container (populated from schema or custom content)
                ColumnLayout {
                    id: fieldsContainer
                    Layout.fillWidth: true
                    spacing: 12

                    // Auto-render fields from schema if available
                    Repeater {
                        model: configModel && configModel.config_schema ?
                               (configModel.config_schema.fields || []) : []

                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            property var fieldSchema: modelData
                            property string fieldType: fieldSchema.type || "string"

                            // Label
                            Label {
                                text: (fieldSchema.label || fieldSchema.name) +
                                      (fieldSchema.required ? " *" : "")
                                font.pixelSize: 12
                                color: "#cccccc"
                                Layout.fillWidth: true
                            }

                            // Text Field (string, password, url)
                            TextField {
                                id: textField
                                Layout.fillWidth: true
                                visible: fieldType === "string" || fieldType === "password" || fieldType === "url"
                                text: configModel ? configModel.get_config_value(fieldSchema.name) || "" : ""
                                echoMode: fieldType === "password" ? TextField.Password : TextField.Normal
                                selectByMouse: true
                                implicitHeight: 32
                                placeholderText: fieldSchema.placeholder || ""

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: textField.activeFocus ? "#3498db" : "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                color: "#ffffff"
                                placeholderTextColor: "#606060"

                                onTextChanged: {
                                    if (configModel) {
                                        configModel.set_config_value(fieldSchema.name, text)
                                    }
                                }
                            }

                            // Checkbox (boolean)
                            RowLayout {
                                Layout.fillWidth: true
                                visible: fieldType === "boolean"
                                spacing: 8

                                CheckBox {
                                    id: boolCheckBox
                                    checked: configModel ? configModel.get_config_value(fieldSchema.name) || false : false

                                    indicator: Rectangle {
                                        implicitWidth: 18
                                        implicitHeight: 18
                                        x: boolCheckBox.leftPadding
                                        y: parent.height / 2 - height / 2
                                        radius: 3
                                        border.color: boolCheckBox.checked ? "#3498db" : "#3a3a3a"
                                        color: boolCheckBox.checked ? "#3498db" : "#1e1e1e"

                                        Text {
                                            visible: boolCheckBox.checked
                                            text: "\u2713"
                                            font.pixelSize: 14
                                            font.bold: true
                                            color: "#ffffff"
                                            anchors.centerIn: parent
                                        }
                                    }

                                    onCheckedChanged: {
                                        if (configModel) {
                                            configModel.set_config_value(fieldSchema.name, checked)
                                        }
                                    }
                                }

                                Label {
                                    text: fieldSchema.description || ""
                                    font.pixelSize: 10
                                    color: "#808080"
                                    Layout.fillWidth: true
                                    wrapMode: Text.WordWrap
                                }
                            }

                            // SpinBox (integer)
                            SpinBox {
                                id: intSpinBox
                                Layout.fillWidth: true
                                visible: fieldType === "integer"
                                value: configModel ? configModel.get_config_value(fieldSchema.name) || 0 : 0
                                from: fieldSchema.min !== undefined ? fieldSchema.min : -2147483648
                                to: fieldSchema.max !== undefined ? fieldSchema.max : 2147483647
                                implicitHeight: 32

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: intSpinBox.activeFocus ? "#3498db" : "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                contentItem: TextInput {
                                    text: intSpinBox.textFromValue(intSpinBox.value, intSpinBox.locale)
                                    font.pixelSize: 12
                                    color: "#ffffff"
                                    selectionColor: "#3498db"
                                    selectedTextColor: "#ffffff"
                                    horizontalAlignment: Qt.AlignHCenter
                                    verticalAlignment: Qt.AlignVCenter
                                    readOnly: !intSpinBox.editable
                                    validator: intSpinBox.validator
                                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                                }

                                up.indicator: Rectangle {
                                    x: intSpinBox.mirrored ? 0 : parent.width - width
                                    height: parent.height
                                    implicitWidth: 30
                                    color: intSpinBox.up.pressed ? "#3498db" : "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3

                                    Text {
                                        text: "+"
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "#ffffff"
                                        anchors.centerIn: parent
                                    }
                                }

                                down.indicator: Rectangle {
                                    x: intSpinBox.mirrored ? parent.width - width : 0
                                    height: parent.height
                                    implicitWidth: 30
                                    color: intSpinBox.down.pressed ? "#3498db" : "#2d2d2d"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3

                                    Text {
                                        text: "-"
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: "#ffffff"
                                        anchors.centerIn: parent
                                    }
                                }

                                onValueChanged: {
                                    if (configModel) {
                                        configModel.set_config_value(fieldSchema.name, value)
                                    }
                                }
                            }

                            // Description text
                            Label {
                                visible: fieldType !== "boolean" && fieldSchema.description
                                text: fieldSchema.description || ""
                                font.pixelSize: 10
                                color: "#606060"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }

                // Spacer
                Item {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 20
                    Layout.preferredHeight: 20
                }
            }
        }
    }
}