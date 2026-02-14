// PlanWidget.qml - Display execution plans
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var planData: ({})  // Expected: {title: "", steps: [{text, status}, ...]}
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#d0d0d0"
    readonly property color titleColor: widgetColor
    readonly property color completedColor: "#51cf66"
    readonly property color pendingColor: "#ffd43b"
    readonly property color failedColor: "#ff6b6b"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    // Calculate height based on content
    readonly property real headerHeight: 40
    readonly property real stepHeight: (planData.steps || []).length > 0 ? (planData.steps || []).length * 28 + 10 : 0
    readonly property real separatorHeight: 1
    implicitHeight: (expanded ? headerHeight + separatorHeight + stepHeight : headerHeight) + 24

    Layout.fillWidth: true

    property bool expanded: true

    ColumnLayout {
        id: planColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 10
        width: parent.width

        // Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // Plan icon
            Text {
                text: "📋"
                font.pixelSize: 16
            }

            // Title
            Text {
                text: root.planData.title || "Execution Plan"
                color: titleColor
                font.pixelSize: 14
                font.weight: Font.Medium
            }

            Item { Layout.fillWidth: true }

            // Toggle
            Text {
                text: root.expanded ? "▼" : "▶"
                color: textColor
                font.pixelSize: 10

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.expanded = !root.expanded
                }
            }
        }

        // Steps
        Loader {
            Layout.fillWidth: true
            Layout.preferredHeight: active ? implicitHeight : 0
            visible: active
            active: root.expanded
            sourceComponent: ColumnLayout {
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 1
                    color: borderColor
                }

                Repeater {
                    model: root.planData.steps || []

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        // Status icon
                        Text {
                            text: {
                                switch (modelData.status || "pending") {
                                    case "completed": return "✅"
                                    case "running": return "⏳"
                                    case "failed": return "❌"
                                    default: return "⏸️"
                                }
                            }
                            font.pixelSize: 14
                        }

                        // Step text
                        Text {
                            Layout.fillWidth: true
                            text: (index + 1) + ". " + (modelData.text || "")
                            color: {
                                switch (modelData.status || "pending") {
                                    case "completed": return completedColor
                                    case "running": return textColor
                                    case "failed": return failedColor
                                    default: return Qt.rgba(textColor.r, textColor.g, textColor.b, 0.6)
                                }
                            }
                            font.pixelSize: 13
                            font.strikeout: modelData.status === "failed"
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        propagateComposedEvents: true
        onPressed: function(mouse) {
            if (mouse.y < 40) {
                root.expanded = !root.expanded
                mouse.accepted = true
            } else {
                mouse.accepted = false
            }
        }
    }
}
