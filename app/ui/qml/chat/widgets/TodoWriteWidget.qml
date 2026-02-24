// TodoWriteWidget.qml - Display and track TODO lists with incremental updates
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var todoData: ({})  // Complete data from content
    property color widgetColor: "#4a90e2"

    // Extract properties from todoData
    property var todos: todoData.todos || todoData.data?.todos || []
    property int total: todoData.total || todoData.data?.total || 0
    property int pending: todoData.pending || todoData.data?.pending || 0
    property int inProgress: todoData.in_progress || todoData.data?.in_progress || 0
    property int completed: todoData.completed || todoData.data?.completed || 0
    property int failed: todoData.failed || todoData.data?.failed || 0
    property int blocked: todoData.blocked || todoData.data?.blocked || 0
    property int version: todoData.version || todoData.data?.version || 0

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#d0d0d0"

    // Status colors
    readonly property color pendingColor: "#888888"
    readonly property color inProgressColor: "#f39c12"
    readonly property color completedColor: "#27ae60"
    readonly property color failedColor: "#e74c3c"
    readonly property color blockedColor: "#9b59b6"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: column.implicitHeight + 16

    Layout.fillWidth: true

    function getSummaryText() {
        if (root.total > 0) {
            return root.completed + "/" + root.total + " completed";
        }
        return "No tasks";
    }

    Column {
        id: column
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 12

        // Header with title and summary
        Row {
            Layout.fillWidth: true
            spacing: 12

            Column {
                spacing: 4
                Layout.fillWidth: true

                Text {
                    text: "📋 TODO List"
                    color: textColor
                    font.pixelSize: 14
                    font.weight: Font.Bold
                }

                Text {
                    text: getSummaryText()
                    color: Qt.rgba(textColor.r, textColor.g, textColor.b, 0.7)
                    font.pixelSize: 11
                }
            }

            // Status badges row
            Row {
                spacing: 6
                anchors.verticalCenter: parent.verticalCenter

                Repeater {
                    model: [
                        {label: "⏳", count: root.pending, color: pendingColor},
                        {label: "🔄", count: root.inProgress, color: inProgressColor},
                        {label: "✅", count: root.completed, color: completedColor},
                        {label: "❌", count: root.failed, color: failedColor},
                        {label: "🚫", count: root.blocked, color: blockedColor}
                    ]
                    delegate: Rectangle {
                        visible: count > 0
                        width: label.implicitWidth + 8
                        height: 20
                        color: modelData.color
                        radius: 10

                        Text {
                            id: label
                            anchors.centerIn: parent
                            text: modelData.label + " " + modelData.count
                            color: "#ffffff"
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }
                    }
                }
            }
        }

        // Progress bar
        Rectangle {
            Layout.fillWidth: true
            height: 6
            color: "#404040"
            radius: 3

            Rectangle {
                width: root.total > 0 ? parent.width * (root.completed / root.total) : 0
                height: parent.height
                color: completedColor
                radius: 3

                Behavior on width {
                    NumberAnimation { duration: 300; easing.type: Easing.InOutQuad }
                }
            }
        }

        // TODO items list
        Column {
            Layout.fillWidth: true
            spacing: 6
            visible: root.todos.length > 0

            Repeater {
                model: root.todos

                delegate: Rectangle {
                    width: parent.width
                    height: itemRow.implicitHeight + 10
                    color: Qt.rgba(bgColor.r, bgColor.g, bgColor.b, 0.5)
                    radius: 4

                    Row {
                        id: itemRow
                        anchors {
                            left: parent.left
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                            margins: 8
                        }
                        spacing: 8

                        // Status icon
                        Text {
                            text: {
                                var status = modelData.status || "pending";
                                if (status === "pending") return "⏳";
                                if (status === "in_progress") return "🔄";
                                if (status === "completed") return "✅";
                                if (status === "failed") return "❌";
                                if (status === "blocked") return "🚫";
                                return "⏳";
                            }
                            font.pixelSize: 14
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        // Task text with selection and copy support
                        SelectableText {
                            width: parent.width - 30
                            text: modelData.title || modelData.description || ""
                            textColor: (modelData.status === "completed") ?
                                   Qt.rgba(textColor.r, textColor.g, textColor.b, 0.5) :
                                   textColor
                            fontPixelSize: 13
                            wrapMode: true
                            selectionColor: root.widgetColor
                        }
                    }
                }
            }
        }
    }
}
