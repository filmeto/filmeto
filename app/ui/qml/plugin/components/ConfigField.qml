// ConfigField.qml - Auto-renders a configuration field based on schema type

import QtQuick 2.15
import QtQuick.Layouts 1.15
import ".."
import "components"

ColumnLayout {
    id: root

    // Field schema definition
    property var fieldSchema: ({})

    // Current value
    property var value: null

    // Reference to the config model for getting/setting values
    property var configModel: null

    signal valueChanged(var newValue)

    spacing: 0

    // Determine field type from schema
    property string fieldType: fieldSchema.type || "string"

    // Render appropriate field type
    Loader {
        id: fieldLoader
        Layout.fillWidth: true
        sourceComponent: {
            switch (fieldType) {
                case "password":
                    return passwordFieldComponent
                case "boolean":
                    return booleanFieldComponent
                case "integer":
                    return integerFieldComponent
                case "select":
                    return selectFieldComponent
                case "url":
                    return urlFieldComponent
                default:
                    return stringFieldComponent
            }
        }

        property var schema: fieldSchema
        property var currentValue: value
    }

    // String field component
    Component {
        id: stringFieldComponent

        StringField {
            label: schema.label || schema.name || ""
            value: currentValue || schema.default || ""
            placeholder: schema.placeholder || ""
            description: schema.description || ""
            required: schema.required || false

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }

    // Password field component
    Component {
        id: passwordFieldComponent

        PasswordField {
            label: schema.label || schema.name || ""
            value: currentValue || schema.default || ""
            placeholder: schema.placeholder || ""
            description: schema.description || ""
            required: schema.required || false

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }

    // Boolean field component
    Component {
        id: booleanFieldComponent

        BooleanField {
            label: schema.label || schema.name || ""
            value: currentValue !== null ? currentValue : (schema.default || false)
            description: schema.description || ""

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }

    // Integer field component
    Component {
        id: integerFieldComponent

        IntegerField {
            label: schema.label || schema.name || ""
            value: currentValue !== null ? currentValue : (schema.default || 0)
            minValue: schema.min !== undefined ? schema.min : -2147483648
            maxValue: schema.max !== undefined ? schema.max : 2147483647
            stepSize: schema.step || 1
            description: schema.description || ""
            required: schema.required || false

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }

    // Select field component
    Component {
        id: selectFieldComponent

        SelectField {
            label: schema.label || schema.name || ""
            value: currentValue || schema.default || ""
            options: schema.options || []
            description: schema.description || ""
            required: schema.required || false

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }

    // URL field component
    Component {
        id: urlFieldComponent

        URLField {
            label: schema.label || schema.name || ""
            value: currentValue || schema.default || ""
            placeholder: schema.placeholder || "https://"
            description: schema.description || ""
            required: schema.required || false

            onValueChanged: function(newValue) {
                root.valueChanged(newValue)
            }
        }
    }
}