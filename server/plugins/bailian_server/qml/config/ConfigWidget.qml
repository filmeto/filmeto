// ConfigWidget.qml - Bailian Server Configuration UI
// Custom QML configuration widget with enhanced UI capabilities

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    color: "#1e1e1e"

    // Configuration model reference (set from Python)
    property var configModel: null

    // Internal state
    property bool codingPlanEnabled: configModel ? configModel.get_config_value("coding_plan_enabled") || false : false

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
            color: "#1e1e1e"
        }

        ColumnLayout {
            id: mainLayout
            width: parent.width - 32
            x: 16
            y: 16
            spacing: 16

            // Header
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Label {
                    text: "Bailian Server Configuration"
                    font.bold: true
                    font.pixelSize: 16
                    color: "#e0e0e0"
                    Layout.fillWidth: true
                }

                Label {
                    text: "Alibaba Cloud DashScope (Bailian) AI Services"
                    font.pixelSize: 12
                    color: "#808080"
                    Layout.fillWidth: true
                }
            }

            // Help Card
            Rectangle {
                Layout.fillWidth: true
                height: helpContent.implicitHeight + 20
                color: "#252525"
                radius: 4

                ColumnLayout {
                    id: helpContent
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 6

                    Label {
                        text: "How to get your API Key:"
                        font.bold: true
                        font.pixelSize: 11
                        color: "#b0b0b0"
                    }

                    Label {
                        text: "1. Go to Alibaba Cloud Console"
                        font.pixelSize: 11
                        color: "#808080"
                    }

                    Label {
                        text: "2. Navigate to DashScope → API-KEY Management"
                        font.pixelSize: 11
                        color: "#808080"
                    }

                    Label {
                        text: "3. Create or copy your API Key"
                        font.pixelSize: 11
                        color: "#808080"
                    }

                    Label {
                        text: "Documentation: help.aliyun.com/zh/model-studio"
                        font.pixelSize: 10
                        color: "#3498db"
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }

            // API Configuration Section
            Rectangle {
                Layout.fillWidth: true
                height: apiLayout.implicitHeight + 20
                color: "#2d2d2d"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: apiLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: "API Configuration"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // API Key Field
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

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: apiKeyField.activeFocus ? "#3498db" : "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                color: "#ffffff"
                                placeholderTextColor: "#606060"
                                placeholderText: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

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
                                implicitWidth: 32
                                implicitHeight: apiKeyField.implicitHeight

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
                    }

                    // Coding Plan Toggle
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        CheckBox {
                            id: codingPlanCheckbox
                            checked: configModel ? configModel.get_config_value("coding_plan_enabled") || false : false

                            indicator: Rectangle {
                                implicitWidth: 18
                                implicitHeight: 18
                                x: codingPlanCheckbox.leftPadding
                                y: parent.height / 2 - height / 2
                                radius: 3
                                border.color: codingPlanCheckbox.checked ? "#3498db" : "#3a3a3a"
                                color: codingPlanCheckbox.checked ? "#3498db" : "#1e1e1e"

                                Text {
                                    visible: codingPlanCheckbox.checked
                                    text: "\u2713"
                                    font.pixelSize: 14
                                    font.bold: true
                                    color: "#ffffff"
                                    anchors.centerIn: parent
                                }
                            }

                            onCheckedChanged: {
                                root.codingPlanEnabled = checked
                                if (configModel) {
                                    configModel.set_config_value("coding_plan_enabled", checked)
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Label {
                                text: "Enable Coding Plan"
                                font.pixelSize: 12
                                color: "#cccccc"
                            }

                            Label {
                                text: "Enable for AI coding assistant (requires separate subscription)"
                                font.pixelSize: 10
                                color: "#808080"
                            }
                        }
                    }

                    // Coding Plan API Key (conditionally visible)
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        visible: root.codingPlanEnabled

                        Behavior on opacity {
                            NumberAnimation { duration: 200 }
                        }
                        opacity: root.codingPlanEnabled ? 1 : 0

                        Label {
                            text: "Coding Plan API Key"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            TextField {
                                id: codingPlanApiKeyField
                                Layout.fillWidth: true
                                text: configModel ? configModel.get_config_value("coding_plan_api_key") || "" : ""
                                echoMode: showCodingPlanApiKey.checked ? TextField.Normal : TextField.Password
                                selectByMouse: true

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: codingPlanApiKeyField.activeFocus ? "#3498db" : "#3a3a3a"
                                    border.width: 1
                                    radius: 3
                                }

                                color: "#ffffff"
                                placeholderTextColor: "#606060"
                                placeholderText: "sk-sp-xxxxxxxx"

                                onTextChanged: {
                                    if (configModel) {
                                        configModel.set_config_value("coding_plan_api_key", text)
                                    }
                                }
                            }

                            ToolButton {
                                id: showCodingPlanApiKey
                                checkable: true
                                checked: false
                                implicitWidth: 32
                                implicitHeight: codingPlanApiKeyField.implicitHeight

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
                            }
                        }

                        Label {
                            text: "Format: sk-sp-xxxxx (get from Coding Plan page)"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }
                }
            }

            // Model Settings Section
            Rectangle {
                Layout.fillWidth: true
                height: modelLayout.implicitHeight + 20
                color: "#2d2d2d"
                radius: 4
                border.color: "#3a3a3a"
                border.width: 1

                ColumnLayout {
                    id: modelLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 12

                    Label {
                        text: "Model Settings (Optional)"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#ffffff"
                    }

                    // Default Chat Model
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Default Chat Model"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: chatModelComboBox
                            Layout.fillWidth: true

                            model: ["qwen-max", "qwen-plus", "qwen-turbo", "qwen-flash", "qwen-vl-max", "qwq-plus"]
                            currentIndex: {
                                var currentModel = configModel ? configModel.get_config_value("default_model") : "qwen-max"
                                var idx = model.indexOf(currentModel)
                                return idx >= 0 ? idx : 0
                            }

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: chatModelComboBox.popup.visible ? "#3498db" :
                                              (chatModelComboBox.hovered ? "#3498db" : "#3a3a3a")
                                radius: 3
                                implicitHeight: 30
                            }

                            contentItem: Text {
                                text: chatModelComboBox.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            indicator: Text {
                                x: chatModelComboBox.width - width - 10
                                y: (chatModelComboBox.height - height) / 2
                                text: "\u25BC"
                                font.pixelSize: 10
                                color: "#808080"
                            }

                            delegate: ItemDelegate {
                                width: chatModelComboBox.width
                                height: 30

                                contentItem: Text {
                                    text: modelData
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#e0e0e0"
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 10
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#1e1e1e"
                                }

                                highlighted: chatModelComboBox.highlightedIndex === index
                            }

                            popup: Popup {
                                y: chatModelComboBox.height
                                width: chatModelComboBox.width
                                implicitHeight: contentItem.implicitHeight
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: chatModelComboBox.popup.visible ? chatModelComboBox.delegateModel : null
                                    currentIndex: chatModelComboBox.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: "#3a3a3a"
                                    radius: 3
                                }
                            }

                            onCurrentTextChanged: {
                                if (configModel) {
                                    configModel.set_config_value("default_model", currentText)
                                }
                            }
                        }

                        Label {
                            text: "Default model for chat completions"
                            font.pixelSize: 10
                            color: "#606060"
                        }
                    }

                    // Default Image Model
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4

                        Label {
                            text: "Default Image Model"
                            font.pixelSize: 12
                            color: "#cccccc"
                        }

                        ComboBox {
                            id: imageModelComboBox
                            Layout.fillWidth: true

                            model: ["wanx2.1-t2i-turbo", "wanx2.1-t2i-plus", "wanx2.6-t2i-turbo", "wanx2.6-t2i-plus"]
                            currentIndex: {
                                var currentModel = configModel ? configModel.get_config_value("default_image_model") : "wanx2.1-t2i-turbo"
                                var idx = model.indexOf(currentModel)
                                return idx >= 0 ? idx : 0
                            }

                            background: Rectangle {
                                color: "#1e1e1e"
                                border.color: imageModelComboBox.popup.visible ? "#3498db" :
                                              (imageModelComboBox.hovered ? "#3498db" : "#3a3a3a")
                                radius: 3
                                implicitHeight: 30
                            }

                            contentItem: Text {
                                text: imageModelComboBox.displayText
                                font.pixelSize: 12
                                color: "#ffffff"
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 10
                            }

                            indicator: Text {
                                x: imageModelComboBox.width - width - 10
                                y: (imageModelComboBox.height - height) / 2
                                text: "\u25BC"
                                font.pixelSize: 10
                                color: "#808080"
                            }

                            delegate: ItemDelegate {
                                width: imageModelComboBox.width
                                height: 30

                                contentItem: Text {
                                    text: modelData
                                    font.pixelSize: 12
                                    color: highlighted ? "#ffffff" : "#e0e0e0"
                                    verticalAlignment: Text.AlignVCenter
                                    leftPadding: 10
                                }

                                background: Rectangle {
                                    color: highlighted ? "#3498db" : "#1e1e1e"
                                }

                                highlighted: imageModelComboBox.highlightedIndex === index
                            }

                            popup: Popup {
                                y: imageModelComboBox.height
                                width: imageModelComboBox.width
                                implicitHeight: contentItem.implicitHeight
                                padding: 1

                                contentItem: ListView {
                                    clip: true
                                    implicitHeight: contentHeight
                                    model: imageModelComboBox.popup.visible ? imageModelComboBox.delegateModel : null
                                    currentIndex: imageModelComboBox.highlightedIndex
                                }

                                background: Rectangle {
                                    color: "#1e1e1e"
                                    border.color: "#3a3a3a"
                                    radius: 3
                                }
                            }

                            onCurrentTextChanged: {
                                if (configModel) {
                                    configModel.set_config_value("default_image_model", currentText)
                                }
                            }
                        }

                        Label {
                            text: "Default model for text-to-image generation"
                            font.pixelSize: 10
                            color: "#606060"
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