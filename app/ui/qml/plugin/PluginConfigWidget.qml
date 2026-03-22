// PluginConfigWidget.qml - Root container for plugin configuration UI
// Automatically renders fields from config_schema if no custom QML is provided

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."
import "components"

Rectangle {
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

    color: Theme.backgroundColor

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

    ScrollView {
        anchors.fill: parent
        clip: true

        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        background: Rectangle {
            color: Theme.backgroundColor
        }

        ColumnLayout {
            id: mainLayout
            width: parent.width
            spacing: 16
            anchors.margins: 16

            // Plugin header
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Label {
                    text: configModel ? configModel.plugin_name : "Plugin Configuration"
                    font.bold: true
                    font.pixelSize: 16
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                }

                // Separator line
                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.border
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

                    delegate: ConfigField {
                        Layout.fillWidth: true

                        fieldSchema: modelData
                        value: configModel ? configModel.get_config_value(modelData.name) : null

                        onValueChanged: function(newValue) {
                            if (configModel) {
                                configModel.set_config_value(modelData.name, newValue)
                            }
                        }
                    }
                }
            }

            // Spacer
            Item {
                Layout.fillHeight: true
                Layout.minimumHeight: 20
            }
        }
    }

    // Animation for smooth appearance
    Behavior on opacity {
        NumberAnimation { duration: 200 }
    }

    Component.onCompleted: {
        opacity = 1
    }
}