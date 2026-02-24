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

        // Header - clickable for expand/collapse
        Item {
            Layout.fillWidth: true
            height: headerRow.implicitHeight

            RowLayout {
                id: headerRow
                width: parent.width
                spacing: 8

                // Plan icon
                Text {
                    text: "📋"
                    font.pixelSize: 16
                }

                // Title with selection support
                SelectableText {
                    Layout.fillWidth: true
                    text: root.planData.title || "Execution Plan"
                    textColor: titleColor
                    fontPixelSize: 14
                    wrapMode: true
                    selectionColor: titleColor
                }

                Item { Layout.fillWidth: true }

                // Toggle
                Text {
                    text: root.expanded ? "▼" : "▶"
                    color: textColor
                    font.pixelSize: 10
                }
            }

            // MouseArea only on header - child components can receive their own clicks
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.expanded = !root.expanded
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

                        // Step text with selection and copy support
                        SelectableText {
                            Layout.fillWidth: true
                            text: (index + 1) + ". " + (modelData.text || "")
                            textColor: {
                                switch (modelData.status || "pending") {
                                    case "completed": return completedColor
                                    case "running": return textColor
                                    case "failed": return failedColor
                                    default: return Qt.rgba(textColor.r, textColor.g, textColor.b, 0.6)
                                }
                            }
                            fontPixelSize: 13
                            wrapMode: true
                            selectionColor: root.titleColor
                        }
                    }
                }
            }
        }
    }
}
