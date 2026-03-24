import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#2b2d30"
    border.color: "#40444b"
    border.width: 1
    radius: 8
    implicitHeight: 136

    property var bridge: agentPromptBridge

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Button {
                id: addContextBtn
                text: "+"
                enabled: bridge ? bridge.enabled : true
                implicitWidth: 24
                implicitHeight: 24
                onClicked: if (bridge) bridge.request_add_context()
            }

            Label {
                visible: !contextRepeater.count
                text: "add context"
                color: "#8b9098"
            }

            Flow {
                Layout.fillWidth: true
                spacing: 6

                Repeater {
                    id: contextRepeater
                    model: bridge ? bridge.contexts : []

                    Rectangle {
                        radius: 10
                        color: "#3a3d45"
                        border.color: "#525764"
                        border.width: 1
                        height: 22
                        width: chipText.implicitWidth + removeBtn.implicitWidth + 16

                        Row {
                            anchors.centerIn: parent
                            spacing: 6

                            Text {
                                id: chipText
                                text: (modelData && modelData.name) ? modelData.name : ""
                                color: "#e7eaf0"
                                font.pixelSize: 12
                            }

                            ToolButton {
                                id: removeBtn
                                text: "x"
                                onClicked: if (bridge && modelData && modelData.id) bridge.request_remove_context(modelData.id)
                            }
                        }
                    }
                }
            }
        }

        TextArea {
            id: inputArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            enabled: bridge ? bridge.enabled : true
            placeholderText: bridge ? bridge.placeholder : "Input Prompts..."
            wrapMode: TextEdit.Wrap
            color: "#e8e8e8"
            selectionColor: "#4a90e2"
            selectedTextColor: "#ffffff"
            text: bridge ? bridge.text : ""
            onTextChanged: if (bridge) bridge.on_text_changed(text)

            Keys.onReturnPressed: function(event) {
                if (event.modifiers & Qt.ShiftModifier) {
                    return
                }
                if (bridge) bridge.submit()
                event.accepted = true
            }
            Keys.onEnterPressed: function(event) {
                if (event.modifiers & Qt.ShiftModifier) {
                    return
                }
                if (bridge) bridge.submit()
                event.accepted = true
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ComboBox {
                id: agentCombo
                enabled: bridge ? bridge.enabled : true
                model: ["Default Agent", "Creative Agent", "Analytical Agent"]
                implicitWidth: 160
            }

            Item { Layout.fillWidth: true }

            Button {
                text: bridge ? bridge.sendLabel : "Send"
                enabled: bridge ? bridge.enabled : true
                onClicked: if (bridge) bridge.submit()
            }
        }
    }
}
