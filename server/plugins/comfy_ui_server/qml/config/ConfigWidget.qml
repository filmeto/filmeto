// ConfigWidget.qml - ComfyUI Server Configuration UI
// Custom QML configuration widget with tabbed layout

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Item {
    id: root

    // configModel is set on the QML engine context by PluginQMLLoader
    // Do not declare a same-named property here - it would shadow the context property

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

    // Cleanup function to properly release focus and close popups
    function cleanup() {
        if (serverUrlField.activeFocus) {
            serverUrlField.deselect()
            serverUrlField.focus = false
        }
        if (apiKeyField.activeFocus) {
            apiKeyField.deselect()
            apiKeyField.focus = false
        }
        root.forceActiveFocus()
    }

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Tab Bar
        TabBar {
            id: tabBar
            Layout.fillWidth: true
            spacing: 2

            background: Rectangle {
                color: "#252525"
            }

            TabButton {
                text: qsTr("⚙ Service")
                width: implicitWidth
                leftPadding: 20
                rightPadding: 20

                background: Rectangle {
                    color: tabBar.currentIndex === 0 ? "#1e1e1e" : (parent.hovered ? "#2d2d2d" : "#252525")
                    border.color: "#3a3a3a"
                    border.width: 1
                    radius: 4

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: tabBar.currentIndex === 0 ? "#1e1e1e" : "#3a3a3a"
                    }
                }

                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    color: tabBar.currentIndex === 0 ? "#ffffff" : "#888888"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                text: qsTr("⚡ Workflows")
                width: implicitWidth
                leftPadding: 20
                rightPadding: 20

                background: Rectangle {
                    color: tabBar.currentIndex === 1 ? "#1e1e1e" : (parent.hovered ? "#2d2d2d" : "#252525")
                    border.color: "#3a3a3a"
                    border.width: 1
                    radius: 4

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: tabBar.currentIndex === 1 ? "#1e1e1e" : "#3a3a3a"
                    }
                }

                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    color: tabBar.currentIndex === 1 ? "#ffffff" : "#888888"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            TabButton {
                text: qsTr("📦 Models")
                width: implicitWidth
                leftPadding: 20
                rightPadding: 20

                background: Rectangle {
                    color: tabBar.currentIndex === 2 ? "#1e1e1e" : (parent.hovered ? "#2d2d2d" : "#252525")
                    border.color: "#3a3a3a"
                    border.width: 1
                    radius: 4

                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 1
                        color: tabBar.currentIndex === 2 ? "#1e1e1e" : "#3a3a3a"
                    }
                }

                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    color: tabBar.currentIndex === 2 ? "#ffffff" : "#888888"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        // Tab content
        StackLayout {
            id: stackLayout
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // ========== Tab 1: Service Configuration ==========
            ScrollView {
                id: serviceScrollView
                clip: true

                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                Flickable {
                    id: serviceFlickable
                    contentWidth: serviceFlickable.width
                    contentHeight: serviceLayout.implicitHeight + 32

                    ColumnLayout {
                        id: serviceLayout
                        width: Math.max(serviceFlickable.width - 32, 400)
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
                                        text: "ComfyUI server address"
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

            // ========== Tab 2: Workflows Management ==========
            Item {
                id: workflowsTab

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    // Header
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Label {
                            text: "Workflows Management"
                            font.bold: true
                            font.pixelSize: 16
                            color: "#e0e0e0"
                            Layout.fillWidth: true
                        }

                        Label {
                            text: "Manage ComfyUI workflows for different generation types"
                            font.pixelSize: 12
                            color: "#808080"
                            Layout.fillWidth: true
                        }
                    }

                    // Workflow List
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "#2d2d2d"
                        border.color: "#3a3a3a"
                        border.width: 1
                        radius: 4

                        ListView {
                            id: workflowList
                            anchors.fill: parent
                            anchors.margins: 4
                            clip: true
                            spacing: 4

                            model: configModel ? configModel.workflows : []

                            delegate: Rectangle {
                                width: workflowList.width - 8
                                height: 72
                                color: mouseArea.containsMouse ? "#303030" : "#252525"
                                radius: 4
                                border.color: "#3a3a3a"
                                border.width: 1

                                property var workflowData: modelData

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 14
                                    anchors.rightMargin: 14
                                    spacing: 14

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 5

                                        Label {
                                            text: workflowData.name || "Unnamed Workflow"
                                            font.bold: true
                                            font.pixelSize: 12
                                            color: "#ffffff"
                                            Layout.fillWidth: true
                                            elide: Text.ElideRight
                                        }

                                        Label {
                                            text: {
                                                var typeText = "Type: " + (workflowData.type || "Unknown")
                                                if (workflowData.description) {
                                                    typeText += " • " + workflowData.description
                                                }
                                                if (workflowData.is_builtin) {
                                                    typeText += " (builtin)"
                                                }
                                                return typeText
                                            }
                                            font.pixelSize: 10
                                            color: "#888888"
                                            Layout.fillWidth: true
                                            wrapMode: Text.WordWrap
                                            elide: Text.ElideRight
                                        }
                                    }

                                    RowLayout {
                                        spacing: 8

                                        Button {
                                            text: qsTr("Edit")
                                            implicitWidth: 65
                                            implicitHeight: 30

                                            background: Rectangle {
                                                color: parent.hovered ? "#666666" : "#555555"
                                                radius: 4
                                            }

                                            contentItem: Text {
                                                text: parent.text
                                                font.pixelSize: 11
                                                color: "#ffffff"
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }

                                        Button {
                                            text: qsTr("Config")
                                            implicitWidth: 65
                                            implicitHeight: 30

                                            background: Rectangle {
                                                color: parent.hovered ? "#5dade2" : "#3498db"
                                                radius: 4
                                            }

                                            contentItem: Text {
                                                text: parent.text
                                                font.pixelSize: 11
                                                font.bold: true
                                                color: "#ffffff"
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                }

                                MouseArea {
                                    id: mouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                }
                            }

                            ScrollBar.vertical: ScrollBar {
                                policy: ScrollBar.AsNeeded
                            }
                        }
                    }
                }
            }

            // ========== Tab 3: Models Configuration ==========
            Item {
                id: modelsTab

                AbilityModelsConfigPanel {
                    anchors.fill: parent
                    anchors.margins: 16
                    amModel: configModel ? configModel.abilityModelsModel : null
                }
            }
        }
    }
}