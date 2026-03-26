// ServiceTab.qml - Service Configuration Tab
// Contains Connection Settings, Authentication, and Performance sections

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ScrollView {
    id: root

    property var configModel: null

    // Cleanup function to release focus from all fields
    function cleanup() {
        var fields = [serverUrlField, apiKeyField]
        for (var i = 0; i < fields.length; i++) {
            if (fields[i] && fields[i].activeFocus) {
                fields[i].deselect()
                fields[i].focus = false
            }
        }
    }

    clip: true
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    Flickable {
        id: flickable
        contentWidth: flickable.width
        contentHeight: contentLayout.implicitHeight + 32

        ColumnLayout {
            id: contentLayout
            width: Math.max(flickable.width - 32, 400)
            x: 16
            y: 16
            spacing: 16

            // Header
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Label {
                    text: "ComfyUI Server Configuration"
                    font.bold: true
                    font.pixelSize: 16
                    color: "#e0e0e0"
                    Layout.fillWidth: true
                }

                Label {
                    text: "Configure connection settings for ComfyUI image/video generation server"
                    font.pixelSize: 12
                    color: "#808080"
                    Layout.fillWidth: true
                }
            }

            // Connection Settings Section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: connectionLayout.implicitHeight + 20
                color: "#2d2d2d"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: connectionLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: "Connection Settings"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // Server URL
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Server URL *"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        TextField {
                            id: serverUrlField
                            Layout.fillWidth: true
                            text: configModel ? configModel.get_config_value("server_url") || "http://192.168.1.100" : "http://192.168.1.100"
                            selectByMouse: true
                            implicitHeight: 32
                            placeholderText: "http://192.168.1.100"

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: serverUrlField.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            color: "#ffffff"
                            placeholderTextColor: "#606060"

                            onTextChanged: {
                                if (configModel) {
                                    configModel.set_config_value("server_url", text)
                                }
                            }
                        }

                        Label {
                            text: "ComfyUI server address (e.g., http://192.168.1.100)"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }

                    // Port
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Port *"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        SpinBox {
                            id: portSpinBox
                            Layout.fillWidth: true
                            value: configModel ? configModel.get_config_value("port") || 8188 : 8188
                            from: 1
                            to: 65535
                            editable: true
                            implicitHeight: 32

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: portSpinBox.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: TextInput {
                                text: portSpinBox.textFromValue(portSpinBox.value, portSpinBox.locale)
                                font.pixelSize: 12
                                color: "#ffffff"
                                selectionColor: "#3498db"
                                selectedTextColor: "#ffffff"
                                horizontalAlignment: Qt.AlignHCenter
                                verticalAlignment: Qt.AlignVCenter
                                readOnly: !portSpinBox.editable
                                validator: portSpinBox.validator
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                            }

                            up.indicator: Rectangle {
                                x: parent.mirrored ? 0 : parent.width - width
                                height: parent.height
                                implicitWidth: 30
                                color: portSpinBox.up.pressed ? "#3498db" : "#2d2d2d"
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
                                x: parent.mirrored ? parent.width - width : 0
                                height: parent.height
                                implicitWidth: 30
                                color: portSpinBox.down.pressed ? "#3498db" : "#2d2d2d"
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
                                    configModel.set_config_value("port", value)
                                }
                            }
                        }

                        Label {
                            text: "ComfyUI server port (default: 8188)"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }

                    // Timeout
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Timeout (seconds)"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        SpinBox {
                            id: timeoutSpinBox
                            Layout.fillWidth: true
                            value: configModel ? configModel.get_config_value("timeout") || 120 : 120
                            from: 10
                            to: 3600
                            editable: true
                            implicitHeight: 32

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: timeoutSpinBox.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: TextInput {
                                text: timeoutSpinBox.textFromValue(timeoutSpinBox.value, timeoutSpinBox.locale)
                                font.pixelSize: 12
                                color: "#ffffff"
                                selectionColor: "#3498db"
                                selectedTextColor: "#ffffff"
                                horizontalAlignment: Qt.AlignHCenter
                                verticalAlignment: Qt.AlignVCenter
                                readOnly: !timeoutSpinBox.editable
                                validator: timeoutSpinBox.validator
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                            }

                            up.indicator: Rectangle {
                                x: parent.mirrored ? 0 : parent.width - width
                                height: parent.height
                                implicitWidth: 30
                                color: timeoutSpinBox.up.pressed ? "#3498db" : "#2d2d2d"
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
                                x: parent.mirrored ? parent.width - width : 0
                                height: parent.height
                                implicitWidth: 30
                                color: timeoutSpinBox.down.pressed ? "#3498db" : "#2d2d2d"
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
                                    configModel.set_config_value("timeout", value)
                                }
                            }
                        }

                        Label {
                            text: "Request timeout in seconds"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }

                    // Enable SSL
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        CheckBox {
                            id: enableSslCheckbox
                            checked: configModel ? configModel.get_config_value("enable_ssl") || false : false

                            indicator: Rectangle {
                                implicitWidth: 18
                                implicitHeight: 18
                                x: enableSslCheckbox.leftPadding
                                y: parent.height / 2 - height / 2
                                radius: 3
                                border.color: enableSslCheckbox.checked ? "#3498db" : "#3a3a3a"
                                color: enableSslCheckbox.checked ? "#3498db" : "#1e1e1e"

                                Text {
                                    visible: enableSslCheckbox.checked
                                    text: "\u2713"
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#ffffff"
                                    anchors.centerIn: parent
                                }
                            }

                            onCheckedChanged: {
                                if (configModel) {
                                    configModel.set_config_value("enable_ssl", checked)
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Label {
                                text: "Enable SSL"
                                font.pixelSize: 12
                                color: "#cccccc"
                            }

                            Label {
                                text: "Use HTTPS connection"
                                font.pixelSize: 10
                                color: "#808080"
                                wrapMode: Text.WordWrap
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            // Authentication Section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: authLayout.implicitHeight + 20
                color: "#2d2d2d"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: authLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: "Authentication"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // API Key
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "API Key"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            TextField {
                                id: apiKeyField
                                Layout.fillWidth: true
                                text: configModel ? configModel.get_config_value("api_key") || "" : ""
                                echoMode: showApiKey.checked ? TextField.Normal : TextField.Password
                                selectByMouse: true
                                implicitHeight: 32
                                placeholderText: "Optional API key"

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: apiKeyField.activeFocus ? "#3498db" : "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                color: "#ffffff"
                                placeholderTextColor: "#606060"

                                onTextChanged: {
                                    if (configModel) {
                                        configModel.set_config_value("api_key", text)
                                    }
                                }
                            }

                            ToolButton {
                                id: showApiKey
                                checkable: true
                                checked: false
                                implicitWidth: 36
                                implicitHeight: 32

                                contentItem: Text {
                                    text: parent.checked ? "\u{1F441}" : "\u{1F576}"
                                    font.pixelSize: 14
                                    color: "#808080"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                ToolTip.text: checked ? "Hide" : "Show"
                                ToolTip.visible: hovered
                            }
                        }

                        Label {
                            text: "Optional API key for authentication"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }
                }
            }

            // Performance Section
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: perfLayout.implicitHeight + 20
                color: "#2d2d2d"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: perfLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: "Performance"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // Max Concurrent Jobs
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Max Concurrent Jobs"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        SpinBox {
                            id: maxJobsSpinBox
                            Layout.fillWidth: true
                            value: configModel ? configModel.get_config_value("max_concurrent_jobs") || 1 : 1
                            from: 1
                            to: 10
                            editable: true
                            implicitHeight: 32

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: maxJobsSpinBox.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: TextInput {
                                text: maxJobsSpinBox.textFromValue(maxJobsSpinBox.value, maxJobsSpinBox.locale)
                                font.pixelSize: 12
                                color: "#ffffff"
                                selectionColor: "#3498db"
                                selectedTextColor: "#ffffff"
                                horizontalAlignment: Qt.AlignHCenter
                                verticalAlignment: Qt.AlignVCenter
                                readOnly: !maxJobsSpinBox.editable
                                validator: maxJobsSpinBox.validator
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                            }

                            up.indicator: Rectangle {
                                x: parent.mirrored ? 0 : parent.width - width
                                height: parent.height
                                implicitWidth: 30
                                color: maxJobsSpinBox.up.pressed ? "#3498db" : "#2d2d2d"
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
                                x: parent.mirrored ? parent.width - width : 0
                                height: parent.height
                                implicitWidth: 30
                                color: maxJobsSpinBox.down.pressed ? "#3498db" : "#2d2d2d"
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
                                    configModel.set_config_value("max_concurrent_jobs", value)
                                }
                            }
                        }

                        Label {
                            text: "Maximum number of concurrent jobs"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }

                    // Queue Timeout
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Queue Timeout (seconds)"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        SpinBox {
                            id: queueTimeoutSpinBox
                            Layout.fillWidth: true
                            value: configModel ? configModel.get_config_value("queue_timeout") || 3200 : 3200
                            from: 60
                            to: 86400
                            editable: true
                            implicitHeight: 32

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: queueTimeoutSpinBox.activeFocus ? "#3498db" : "#3a3a3a"
                                border.width: 1
                                radius: 3
                            }

                            contentItem: TextInput {
                                text: queueTimeoutSpinBox.textFromValue(queueTimeoutSpinBox.value, queueTimeoutSpinBox.locale)
                                font.pixelSize: 12
                                color: "#ffffff"
                                selectionColor: "#3498db"
                                selectedTextColor: "#ffffff"
                                horizontalAlignment: Qt.AlignHCenter
                                verticalAlignment: Qt.AlignVCenter
                                readOnly: !queueTimeoutSpinBox.editable
                                validator: queueTimeoutSpinBox.validator
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                            }

                            up.indicator: Rectangle {
                                x: parent.mirrored ? 0 : parent.width - width
                                height: parent.height
                                implicitWidth: 30
                                color: queueTimeoutSpinBox.up.pressed ? "#3498db" : "#2d2d2d"
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
                                x: parent.mirrored ? parent.width - width : 0
                                height: parent.height
                                implicitWidth: 30
                                color: queueTimeoutSpinBox.down.pressed ? "#3498db" : "#2d2d2d"
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
                                    configModel.set_config_value("queue_timeout", value)
                                }
                            }
                        }

                        Label {
                            text: "Maximum time to wait in queue"
                            font.pixelSize: 10
                            color: "#606060"
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