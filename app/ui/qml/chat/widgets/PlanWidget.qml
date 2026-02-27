// PlanWidget.qml - Unified plan widget for both inline and panel use
//
// This widget supports two modes:
// 1. Inline mode: Used in chat messages with static planData
// 2. Panel mode: Connected to PlanBridge for real-time updates
//
// Features:
// - Collapsible header with status counts
// - Task list with crew member info
// - Real-time updates via bridge
// - Smooth animations
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    // === Input Properties ===

    // Static plan data for inline mode (format: {title, steps, tasks, plan_id, ...})
    property var planData: ({})

    // Bridge for real-time updates (panel mode)
    property var planBridge: null

    // Mode: "inline" for chat messages, "panel" for sidebar
    property string mode: "inline"

    // Styling
    property color widgetColor: "#4a90e2"
    property color bgColor: "#252525"
    property color headerColor: "#2b2d30"
    property color borderColor: "#3a3a3a"
    property color textColor: "#e1e1e1"
    property color dimTextColor: "#9a9a9a"

    // Status colors
    property color runningColor: "#f4c542"
    property color waitingColor: "#3498db"
    property color completedColor: "#2ecc71"
    property color failedColor: "#e74c3c"

    // State
    property bool isExpanded: false

    // Custom signal for external listeners (renamed to avoid conflict with auto-generated signal)
    signal expandedChanged(bool expanded)

    // Emit custom signal when isExpanded changes
    onIsExpandedChanged: {
        root.expandedChanged(root.isExpanded)
    }

    property bool hasPlan: {
        if (mode === "panel") {
            // Use explicit boolean conversion to handle undefined
            if (planBridge && typeof planBridge.hasPlan === 'boolean') {
                return planBridge.hasPlan
            }
            return false
        }
        // Inline mode: check for plan_id or title/steps
        if (!planData || typeof planData !== "object") return false
        return (planData.plan_id && planData.plan_id.length > 0) ||
               (planData.title && planData.title.length > 0) ||
               (planData.steps && planData.steps.length > 0) ||
               (planData.tasks && planData.tasks.length > 0)
    }
    property bool hasTasks: tasksModel.length > 0

    // Computed properties based on mode
    readonly property var currentTasks: {
        if (mode === "panel" && planBridge) {
            return planBridge.tasks || []
        }
        // Inline mode: use tasks from planData, or convert steps
        if (planData && planData.tasks) {
            return planData.tasks
        }
        if (planData && planData.steps) {
            return planData.steps.map(function(step, index) {
                return {
                    id: step.id || ("task_" + index),
                    name: step.text || step.name || "Task",
                    status: step.status || "waiting",
                    description: step.description || "",
                    crew_member: step.crew_member || null
                }
            })
        }
        return []
    }

    readonly property var tasksModel: currentTasks

    readonly property int runningCount: {
        if (mode === "panel" && planBridge) return planBridge.runningCount
        return countByStatus("running")
    }

    readonly property int waitingCount: {
        if (mode === "panel" && planBridge) return planBridge.waitingCount
        return countByStatus("created") + countByStatus("ready") + countByStatus("waiting")
    }

    readonly property int completedCount: {
        if (mode === "panel" && planBridge) return planBridge.completedCount
        return countByStatus("completed")
    }

    readonly property int failedCount: {
        if (mode === "panel" && planBridge) return planBridge.failedCount
        return countByStatus("failed") + countByStatus("cancelled")
    }

    readonly property string planTitle: {
        if (mode === "panel" && planBridge) return planBridge.planName
        return planData ? (planData.title || planData.plan_title || "Execution Plan") : "Execution Plan"
    }

    readonly property string summaryText: {
        if (mode === "panel" && planBridge) return planBridge.summaryText
        return planTitle
    }

    // === Layout ===

    // Padding around the content
    property int contentPadding: 6

    // Calculate implicit dimensions based on content
    // Header is always visible (40px), details only when expanded
    readonly property int headerImplicitHeight: 40
    readonly property int detailsImplicitHeight: {
        if (!root.isExpanded || !hasTasks) return 0
        // Calculate based on task count, capped at maxDetailsHeight
        var taskHeight = 50  // Approximate height per task item
        var calculatedHeight = tasksModel.length * taskHeight + 24
        return Math.min(calculatedHeight, mode === "panel" ? 200 : 400)
    }
    implicitHeight: headerImplicitHeight + detailsImplicitHeight + contentPadding * 2
    implicitWidth: 200
    // Background color based on mode: panel mode uses solid background, inline mode is transparent
    color: mode === "panel" ? "#2b2d30" : "transparent"
    // No rounded corners in panel mode for better integration, rounded in inline mode
    radius: mode === "panel" ? 0 : 6

    // Helper functions
    function countByStatus(status) {
        var count = 0
        for (var i = 0; i < tasksModel.length; i++) {
            if (tasksModel[i].status === status) count++
        }
        return count
    }

    function getStatusColor(status) {
        switch (status) {
            case "running": return runningColor
            case "completed": return completedColor
            case "failed":
            case "cancelled": return failedColor
            default: return waitingColor
        }
    }

    function getStatusIcon(status) {
        switch (status) {
            case "running": return "R"
            case "completed": return "S"
            case "failed":
            case "cancelled": return "F"
            default: return "W"
        }
    }

    function getStatusEmoji(status) {
        switch (status) {
            case "running": return "⏳"
            case "completed": return "✅"
            case "failed":
            case "cancelled": return "❌"
            default: return "⏸️"
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: contentPadding
        }
        spacing: 0

        // === Header ===
        Rectangle {
            id: headerRect
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            // No rounded corners in panel mode
            radius: mode === "panel" ? 0 : 6
            color: headerColor

            // Bottom corners rounded only when collapsed (only in inline mode)
            Rectangle {
                visible: root.isExpanded && mode !== "panel"
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: parent.radius
                color: parent.color
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 8

                // Plan icon
                Rectangle {
                    width: 20
                    height: 20
                    radius: 10
                    color: widgetColor

                    Text {
                        anchors.centerIn: parent
                        text: "P"
                        color: "white"
                        font.pixelSize: 10
                        font.bold: true
                    }
                }

                // Summary text
                Text {
                    id: summaryTextItem
                    Layout.fillWidth: true
                    text: summaryText
                    color: textColor
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                // Status counts
                Item { Layout.preferredWidth: 4 }

                // Running count
                StatusCountBadge {
                    visible: runningCount > 0
                    label: "R"
                    count: runningCount
                    badgeColor: runningColor
                }

                // Waiting count
                StatusCountBadge {
                    visible: waitingCount > 0
                    label: "W"
                    count: waitingCount
                    badgeColor: waitingColor
                }

                // Completed count
                StatusCountBadge {
                    visible: completedCount > 0
                    label: "S"
                    count: completedCount
                    badgeColor: completedColor
                }

                // Failed count
                StatusCountBadge {
                    visible: failedCount > 0
                    label: "F"
                    count: failedCount
                    badgeColor: failedColor
                }

                // Expand/collapse arrow
                Text {
                    visible: hasTasks
                    text: root.isExpanded ? "▲" : "▼"
                    color: dimTextColor
                    font.pixelSize: 9
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: hasTasks ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (hasTasks) {
                        root.isExpanded = !root.isExpanded
                    }
                }
            }
        }

        // === Details (expanded) ===
        Rectangle {
            id: detailsRect
            Layout.fillWidth: true
            Layout.topMargin: 0
            // Calculate height but cap it at a maximum for panel mode
            readonly property int contentHeight: detailsContent.height + 12
            readonly property int maxDetailsHeight: mode === "panel" ? 200 : 400
            Layout.preferredHeight: root.isExpanded ? Math.min(contentHeight, maxDetailsHeight) : 0
            visible: root.isExpanded && hasTasks
            clip: true
            color: bgColor
            // No rounded corners in panel mode
            radius: mode === "panel" ? 0 : 6

            // Top corners rounded only when expanded (only in inline mode)
            Rectangle {
                visible: root.isExpanded && mode !== "panel"
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: parent.radius
                color: parent.color
            }

            Behavior on Layout.preferredHeight {
                NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
            }

            // ScrollView for task list when content exceeds available space
            ScrollView {
                id: detailsScrollView
                anchors.fill: parent
                anchors.margins: 6
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AsNeeded
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                background: Rectangle {
                    color: "transparent"
                }

                Column {
                    id: detailsContent
                    width: detailsScrollView.width - 12
                    spacing: 6

                    Repeater {
                        model: tasksModel

                        delegate: Rectangle {
                            width: detailsContent.width
                            height: taskRowColumn.height + 12
                            color: "#2b2d30"
                            radius: 4

                            ColumnLayout {
                                id: taskRowColumn
                                anchors {
                                    left: parent.left
                                    right: parent.right
                                    top: parent.top
                                    margins: 6
                                }
                                spacing: 4

                                // Task row: status + name
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    // Status icon
                                    Rectangle {
                                        width: 14
                                        height: 14
                                        radius: 7
                                        color: getStatusColor(modelData.status)

                                        Text {
                                            anchors.centerIn: parent
                                            text: getStatusIcon(modelData.status)
                                            color: "white"
                                            font.pixelSize: 8
                                            font.bold: true
                                        }
                                    }

                                    // Task name
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.name || "Untitled Task"
                                        color: textColor
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                        maximumLineCount: 1
                                        wrapMode: Text.NoWrap
                                    }
                                }

                                // Crew member row
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6

                                    // Crew avatar
                                    Rectangle {
                                        width: 16
                                        height: 16
                                        radius: 3
                                        color: {
                                            var cm = modelData.crew_member
                                            return cm ? cm.color : "#5c5f66"
                                        }

                                        Text {
                                            anchors.centerIn: parent
                                            text: {
                                                var cm = modelData.crew_member
                                                return cm ? (cm.icon || "A") : "A"
                                            }
                                            color: "white"
                                            font.pixelSize: 9
                                            font.bold: true
                                        }
                                    }

                                    // Crew name
                                    Text {
                                        text: {
                                            var cm = modelData.crew_member
                                            if (cm && cm.name) return cm.name
                                            return modelData.title || "Unknown"
                                        }
                                        color: dimTextColor
                                        font.pixelSize: 11
                                    }

                                    Item { Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                }
            }
        }

        // === Empty state ===
        Text {
            Layout.fillWidth: true
            Layout.topMargin: 8
            visible: !hasPlan || !hasTasks
            text: hasPlan ? qsTr("No tasks available") : qsTr("No active plan")
            color: dimTextColor
            font.pixelSize: 12
            horizontalAlignment: Text.AlignHCenter
        }
    }

    // === Reusable Components ===

    // Status count badge component
    component StatusCountBadge: Row {
        spacing: 4

        property string label: ""
        property int count: 0
        property color badgeColor: "white"

        Rectangle {
            width: 12
            height: 12
            radius: 6
            color: badgeColor

            Text {
                anchors.centerIn: parent
                text: label
                color: "white"
                font.pixelSize: 8
                font.bold: true
            }
        }

        Text {
            text: count.toString()
            color: textColor
            font.pixelSize: 12
        }
    }
}
