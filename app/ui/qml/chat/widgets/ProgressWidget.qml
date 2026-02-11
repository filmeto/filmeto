// ProgressWidget.qml - Progress indicator for long-running operations
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string text: ""
    property var percentage: null  // null for indeterminate, or number 0-100
    property color widgetColor: "#4a90e2"

    readonly property color textColor: "#d0d0d0"
    readonly property color bulletColor: widgetColor

    implicitWidth: parent.width
    implicitHeight: row.implicitHeight

    Layout.fillWidth: true

    RowLayout {
        id: row
        anchors {
            left: parent.left
            right: parent.right
        }
        spacing: 8

        // Bullet point (like li)
        Rectangle {
            Layout.preferredWidth: 6
            Layout.preferredHeight: 6
            Layout.alignment: Qt.AlignTop

            radius: width / 2
            color: bulletColor
        }

        // Progress text with percentage
        Text {
            Layout.fillWidth: true
            text: root.percentage !== null ?
                  root.text + " (" + Math.round(root.percentage) + "%)" :
                  root.text
            color: textColor
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }
    }
}
