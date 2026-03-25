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
                enabled: bridge ? (bridge.enabled && !bridge.conversationActive) : true
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

                    ContextItemWidget {
                        contextId: (modelData && modelData.id) ? modelData.id : ""
                        contextName: (modelData && modelData.name) ? modelData.name : ""
                        onRemoveRequested: function(id) {
                            if (bridge && id) bridge.request_remove_context(id)
                        }
                    }
                }
            }
        }

        TextArea {
            id: inputArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            enabled: bridge ? (bridge.enabled && !bridge.conversationActive) : true
            placeholderText: bridge ? bridge.placeholder : "Input Prompts..."
            wrapMode: TextEdit.Wrap
            color: "#e8e8e8"
            selectionColor: "#4a90e2"
            selectedTextColor: "#ffffff"
            text: bridge ? bridge.text : ""
            onTextChanged: if (bridge) bridge.on_text_changed(text)

            Keys.onPressed: function(event) {
                if (!bridge) return

                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                    // Shift/Ctrl+Enter inserts newline; plain Enter submits.
                    if (event.modifiers & Qt.ShiftModifier) return
                    if (event.modifiers & Qt.ControlModifier) return

                    bridge.submit()
                    event.accepted = true
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            ComboBox {
                id: agentCombo
                enabled: bridge ? (bridge.enabled && !bridge.conversationActive) : true
                model: ["Default Agent", "Creative Agent", "Analytical Agent"]
                implicitWidth: 160
            }

            Item { Layout.fillWidth: true }

            Button {
                id: cancelBtn
                text: "Cancel"
                visible: bridge ? bridge.conversationActive : false
                enabled: bridge ? bridge.enabled : true
                onClicked: if (bridge) bridge.request_cancel()
            }

            Button {
                text: bridge ? bridge.sendLabel : "Send"
                enabled: bridge ? (bridge.enabled && !bridge.conversationActive) : true
                visible: bridge ? !bridge.conversationActive : true
                onClicked: if (bridge) bridge.submit()
            }
        }
    }
}
