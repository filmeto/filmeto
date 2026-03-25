import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#2b2d30"
    border.color: "#505254"
    border.width: 1
    radius: 8
    implicitHeight: 136

    property var bridge: agentPromptBridge

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        // Context row with add button and chips
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            // Add context button - styled like tool buttons
            Rectangle {
                id: addContextBtn
                implicitWidth: 28
                implicitHeight: 28
                radius: 6
                color: addContextMouseArea.containsPress ? "#2c2f31" : (addContextMouseArea.containsMouse ? "#4c5052" : "#3c3f41")
                border.color: "#555555"
                border.width: 1
                enabled: bridge ? bridge.enabled : true

                Text {
                    anchors.centerIn: parent
                    text: "+"
                    color: enabled ? "#e8e8e8" : "#666666"
                    font.pixelSize: 16
                    font.bold: true
                }

                MouseArea {
                    id: addContextMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (bridge) bridge.request_add_context()
                }
            }

            Label {
                visible: !contextRepeater.count
                text: "add context"
                color: "#8b9098"
                font.pixelSize: 12
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
                        width: chipRow.implicitWidth + 16

                        Row {
                            id: chipRow
                            anchors.centerIn: parent
                            spacing: 6

                            Text {
                                id: chipText
                                text: (modelData && modelData.name) ? modelData.name : ""
                                color: "#e7eaf0"
                                font.pixelSize: 12
                            }

                            // Remove button styled as small tool button
                            Rectangle {
                                id: removeBtn
                                width: 14
                                height: 14
                                radius: 7
                                color: removeMouseArea.containsPress ? "#c75450" : (removeMouseArea.containsMouse ? "#d46460" : "#555555")

                                Text {
                                    anchors.centerIn: parent
                                    text: "×"
                                    color: "white"
                                    font.pixelSize: 10
                                    font.bold: true
                                }

                                MouseArea {
                                    id: removeMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: if (bridge && modelData && modelData.id) bridge.request_remove_context(modelData.id)
                                }
                            }
                        }
                    }
                }
            }
        }

        // Text input area - styled like QTextEdit
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#1e1e1e"
            border.color: inputArea.activeFocus ? "#4a90e2" : "#40444b"
            border.width: 1
            radius: 4

            TextArea {
                id: inputArea
                anchors.fill: parent
                anchors.margins: 4
                enabled: bridge ? bridge.enabled : true
                placeholderText: bridge ? bridge.placeholder : "Input Prompts..."
                wrapMode: TextEdit.Wrap
                color: "#e8e8e8"
                selectionColor: "#4a90e2"
                selectedTextColor: "#ffffff"
                text: bridge ? bridge.text : ""
                onTextChanged: if (bridge) bridge.on_text_changed(text)

                // Remove default background
                background: Rectangle {
                    color: "transparent"
                }

                font.pixelSize: 14

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
        }

        // Bottom row with agent selector and send button
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Agent selector styled like QComboBox
            Rectangle {
                implicitWidth: 160
                implicitHeight: 28
                color: agentComboMouseArea.containsPress ? "#2c2f31" : (agentComboMouseArea.containsHover ? "#4c5052" : "#3c3f41")
                border.color: "#555555"
                border.width: 1
                radius: 4
                enabled: bridge ? bridge.enabled : true

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    spacing: 4

                    Text {
                        text: agentCombo.currentText
                        color: enabled ? "#e8e8e8" : "#666666"
                        font.pixelSize: 13
                        Layout.fillWidth: true
                    }

                    Text {
                        text: "▼"
                        color: enabled ? "#8b9098" : "#555555"
                        font.pixelSize: 10
                    }
                }

                MouseArea {
                    id: agentComboMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: agentCombo.popup.open()
                }

                ComboBox {
                    id: agentCombo
                    visible: false
                    model: ["Default Agent", "Creative Agent", "Analytical Agent"]
                }
            }

            Item { Layout.fillWidth: true }

            // Send button - styled like primary action button
            Rectangle {
                id: sendBtn
                implicitWidth: sendText.implicitWidth + 24
                implicitHeight: 28
                radius: 4
                color: {
                    if (!enabled) return "#2c3a4a"
                    if (sendMouseArea.containsPress) return "#2a4a7a"
                    if (sendMouseArea.containsHover) return "#4a7ab0"
                    return "#365880"
                }
                enabled: bridge ? bridge.enabled : true

                Text {
                    id: sendText
                    anchors.centerIn: parent
                    text: bridge ? bridge.sendLabel : "Send"
                    color: enabled ? "#ffffff" : "#888888"
                    font.pixelSize: 13
                    font.bold: true
                }

                MouseArea {
                    id: sendMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: if (bridge) bridge.submit()
                }
            }
        }
    }
}
