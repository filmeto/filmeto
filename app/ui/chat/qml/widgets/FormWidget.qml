// FormWidget.qml - Widget for displaying form content
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var formData: ({})  // Expected: {fields: [{name, type, label, value, options}]}
    property string title: ""
    property color widgetColor: "#4a90e2"

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: formColumn.height + 24

    signal formSubmitted(var data)

    Column {
        id: formColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 12

        // Title
        Text {
            id: titleText
            width: parent.width
            text: root.title
            color: "#e0e0e0"
            font.pixelSize: 13
            font.weight: Font.Medium
            visible: root.title !== ""
        }

        // Form fields
        Repeater {
            model: formData.fields || []

            Column {
                width: parent.width
                spacing: 4

                Text {
                    text: modelData.label || modelData.name
                    color: "#888888"
                    font.pixelSize: 11
                }

                // Text input
                TextField {
                    width: parent.width
                    placeholderText: modelData.placeholder || ""
                    visible: modelData.type === "text" || !modelData.type
                }

                // Text area
                TextArea {
                    width: parent.width
                    placeholderText: modelData.placeholder || ""
                    visible: modelData.type === "textarea"
                }

                // Select dropdown
                ComboBox {
                    width: parent.width
                    model: modelData.options || []
                    visible: modelData.type === "select"
                }

                // Checkbox
                CheckBox {
                    text: modelData.label || modelData.name
                    visible: modelData.type === "checkbox"
                }
            }
        }

        // Submit button
        Button {
            text: "Submit"
            visible: formData.fields && formData.fields.length > 0
            onClicked: {
                // Collect form data
                var data = {}
                for (var i = 0; i < formData.fields.length; i++) {
                    data[formData.fields[i].name] = formData.fields[i].value || ""
                }
                root.formSubmitted(data)
            }
        }
    }
}
