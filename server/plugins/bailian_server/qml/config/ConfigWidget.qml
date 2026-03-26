// ConfigWidget.qml - Bailian Server Configuration UI
// Custom QML configuration widget with enhanced UI capabilities

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

Item {
    id: root

    // configModel is set on the QML engine context by PluginQMLLoader; do not declare a
    // same-named property here — it would shadow the context property and stay null.

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

    // Cleanup function to properly release focus and close popups
    // Called from Python before widget destruction
    function cleanup() {
        // Clear text selection and focus from TextField
        if (apiKeyField.activeFocus) {
            apiKeyField.deselect()
            apiKeyField.focus = false
        }
        if (codingPlanApiKeyField.activeFocus) {
            codingPlanApiKeyField.deselect()
            codingPlanApiKeyField.focus = false
        }

        // Force focus release from any focused item
        root.forceActiveFocus()
    }

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ScrollView {
        id: scrollView
        anchors.fill: parent
        clip: true

        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Flickable {
            id: flickable
            contentWidth: flickable.width
            contentHeight: mainLayout.implicitHeight + 32

            ColumnLayout {
                id: mainLayout
                width: Math.max(flickable.width - 32, 400)
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
                    implicitHeight: helpContent.implicitHeight + 20
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
                    implicitHeight: apiLayout.implicitHeight + 20
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
                                    implicitHeight: 32

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
                                    wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        // Coding Plan API Key (conditionally visible)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4
                            visible: root.codingPlanEnabled
                            implicitHeight: root.codingPlanEnabled ? implicitHeight : 0

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
                                    implicitHeight: 32

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

                AbilityModelsConfigPanel {
                    Layout.fillWidth: true
                    amModel: configModel ? configModel.abilityModelsModel : null
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
}