// DateSeparator.qml - Date grouping separator for messages
import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string dateText: ""

    implicitWidth: parent ? parent.width : 400
    implicitHeight: 24

    // Centered date label
    RowLayout {
        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
        }
        spacing: 12

        // Left line
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#404040"
        }

        // Date text
        Text {
            text: dateText
            color: "#808080"
            font.pixelSize: 11
            font.weight: Font.Medium
        }

        // Right line
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#404040"
        }
    }
}
