// PlanTaskWidget.qml - Lightweight widget for PlanTask status updates
//
// This widget displays a single task status change using TaskItemDelegate.
// It is shown in the Thinking section for plan task updates.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    // Input data
    property var updateData: ({})

    // Styling
    property color widgetColor: "#4a90e2"
    property color textColor: "#e1e1e1"
    property color dimTextColor: "#9a9a9a"
    readonly property color bgColor: "#252525"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent ? parent.width : 200
    implicitHeight: taskDelegate.height + 16
    Layout.fillWidth: true

    // Status colors
    property color runningColor: "#f4c542"
    property color waitingColor: "#3498db"
    property color completedColor: "#2ecc71"
    property color failedColor: "#e74c3c"

    // Previous and current status
    readonly property string previousStatus: updateData.previous_status || ""
    readonly property string currentStatus: updateData.task_status || "waiting"

    // Build task data for TaskItemDelegate
    readonly property var taskData: ({
        id: updateData.task_id || "",
        name: updateData.task_name || qsTr("Task Updated"),
        status: currentStatus,
        description: updateData.description || "",
        title: updateData.crew_member ? updateData.crew_member.name : "",
        crew_member: updateData.crew_member || null,
        needs: updateData.needs || [],
        error_message: updateData.error_message || ""
    })

    // Task Item Delegate - shows start/end status and description
    TaskItemDelegate {
        id: taskDelegate
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: 8
        }

        taskData: root.taskData
        widgetColor: root.widgetColor
        bgColor: "#2b2d30"
        textColor: root.textColor
        dimTextColor: root.dimTextColor
        runningColor: root.runningColor
        waitingColor: root.waitingColor
        completedColor: root.completedColor
        failedColor: root.failedColor

        // Show status transition (start -> end)
        showStatusTransition: true
        previousStatus: root.previousStatus

        // Hide crew member info in PlanTaskWidget
        showCrewMember: false
    }
}
