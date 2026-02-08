// TaskListWidget.qml - Widget for displaying task list
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var tasks: []  // Array of {id, title, completed, status}
    property string title: "Tasks"
    property color widgetColor: "#4a90e2"

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: taskListColumn.height + 24

    signal taskToggled(string taskId, bool completed)

    Column {
        id: taskListColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        // Title
        Text {
            id: titleText
            width: parent.width
            text: root.title + " (" + (root.tasks ? root.tasks.length : 0) + ")"
            color: "#e0e0e0"
            font.pixelSize: 13
            font.weight: Font.Medium
        }

        // Task list
        Repeater {
            model: root.tasks || []

            Row {
                spacing: 10
                width: parent.width

                CheckBox {
                    id: taskCheckBox
                    checked: modelData.completed || false
                    anchors.verticalCenter: parent.verticalCenter

                    onClicked: {
                        root.taskToggled(modelData.id, checked)
                    }
                }

                Text {
                    id: taskText
                    text: modelData.title || ""
                    color: modelData.completed ? "#666666" : "#e0e0e0"
                    font.pixelSize: 12
                    font.strikeout: modelData.completed || false
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - taskCheckBox.width - parent.spacing
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
