// ConfigWidget.qml - ComfyUI Server Configuration UI
// Custom QML configuration widget with tabbed layout

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import plugin 1.0
import "dialogs" as Dialogs

Item {
    id: root

    // configModel is set on the QML engine context by PluginQMLLoader
    property var configModel: null

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

    // Cleanup function - release focus from all text fields
    function cleanup() {
        // Clear focus from ServiceTab fields via its cleanup function
        if (serviceTab && typeof serviceTab.cleanup === 'function') {
            serviceTab.cleanup()
        }
        root.forceActiveFocus()
    }

    Component.onCompleted: {
        // Get configModel from parent context if not set
        if (!configModel && parent && parent.configModel) {
            configModel = parent.configModel
        }
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

            // Tab 1: Service Configuration
            ServiceTab {
                id: serviceTab
                configModel: root.configModel
            }

            // Tab 2: Workflows Management
            WorkflowsTab {
                configModel: root.configModel
            }

            // Tab 3: Models Configuration
            ModelsTab {
                configModel: root.configModel
            }
        }
    }
}