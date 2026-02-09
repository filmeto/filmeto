// FormWidget.qml - Interactive form widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var formData: ({})  // {fields: [{name, type, label, placeholder, options}]}
    property color widgetColor: "#4a90e2"
    property var onFormSubmit: null  // Callback when form is submitted

    implicitWidth: parent.width
    implicitHeight: formColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: formColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 12

        // Form title
        Text {
            visible: formData.title && formData.title > ""
            width: parent.width
            text: formData.title || ""
            color: "#e0e0e0"
            font.pixelSize: 14
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
        }

        // Form description
        Text {
            visible: formData.description && formData.description > ""
            width: parent.width
            text: formData.description || ""
            color: "#a0a0a0"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }

        // Form fields
        Repeater {
            model: formData.fields || []

            delegate: Column {
                width: parent.width
                spacing: 4

                // Field label
                Text {
                    width: parent.width
                    text: modelData.label || modelData.name || ""
                    color: "#d0d0d0"
                    font.pixelSize: 12
                    visible: modelData.label && modelData.label > ""
                }

                // Text input
                TextField {
                    visible: modelData.type === "text" || modelData.type === undefined || modelData.type === null
                    width: parent.width
                    placeholderText: modelData.placeholder || ""
                    color: "#e0e0e0"
                    background: Rectangle {
                        color: "#404040"
                        radius: 4
                        border.color: "#606060"
                        border.width: 1
                    }
                }

                // Text area
                ScrollView {
                    visible: modelData.type === "textarea"
                    width: parent.width
                    height: 80
                    clip: true

                    TextArea {
                        width: parent.width
                        placeholderText: modelData.placeholder || ""
                        color: "#e0e0e0"
                        wrapMode: TextArea.Wrap
                        background: Rectangle {
                            color: "#404040"
                            radius: 4
                            border.color: "#606060"
                            border.width: 1
                        }
                    }
                }

                // Dropdown/ComboBox
                ComboBox {
                    visible: modelData.type === "select"
                    width: parent.width
                    model: modelData.options || []
                    textRole: modelData.textRole || ""
                }

                // Checkbox
                CheckBox {
                    visible: modelData.type === "checkbox"
                    text: modelData.label || ""
                    contentItem: Text {
                        text: parent.text
                        color: "#d0d0d0"
                        leftPadding: parent.indicator.width + parent.spacing
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                // Number input
                SpinBox {
                    visible: modelData.type === "number"
                    width: parent.width
                    from: modelData.min || -9999
                    to: modelData.max || 9999
                    value: modelData.value || 0
                }
            }
        }

        // Submit button
        Button {
            visible: formData.submitText && formData.submitText > ""
            width: parent.width
            text: formData.submitText || "Submit"

            background: Rectangle {
                color: root.widgetColor
                radius: 4
            }

            contentItem: Text {
                text: parent.text
                color: "#ffffff"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 13
            }

            onClicked: {
                if (root.onFormSubmit !== null) {
                    // Collect form data
                    var formValues = {}
                    // Form submission logic would go here
                    root.onFormSubmit(formValues)
                }
            }
        }
    }
}
