// ProgressWidget.qml - Progress indicator for long-running operations
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string text: ""
    property var percentage: null  // null for indeterminate, or number 0-100
    property color widgetColor: "#4a90e2"

    readonly property color bgColor: "#2a2a2a"
    readonly property color borderColor: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    readonly property color textColor: "#d0d0d0"
    readonly property color progressColor: widgetColor

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    width: parent ? parent.width : 0
    height: column.implicitHeight + 20  // 2 * margins (10)
    implicitWidth: width
    implicitHeight: height

    Layout.fillWidth: true

    ColumnLayout {
        id: column
        anchors {
            fill: parent
            margins: 10
        }
        spacing: 8

        // Progress text
        Text {
            Layout.fillWidth: true
            text: root.text
            color: textColor
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }

        // Progress bar
        ProgressBar {
            Layout.fillWidth: true

            indeterminate: root.percentage === null
            value: root.percentage !== null ? root.percentage / 100 : 0

            background: Rectangle {
                implicitWidth: 200
                implicitHeight: 6
                color: "#404040"
                radius: height / 2
            }

            contentItem: Rectangle {
                implicitWidth: 200
                implicitHeight: 6
                color: progressColor
                radius: height / 2
                width: root.percentage !== null ?
                       parent.width * (root.percentage / 100) :
                       indeterminateWidth * parent.width

                property real indeterminateWidth: 0.3

                // Animation for indeterminate state
                SequentialAnimation on indeterminateWidth {
                    running: root.percentage === null
                    loops: Animation.Infinite
                    NumberAnimation {
                        from: 0.1
                        to: 0.7
                        duration: 1000
                    }
                    NumberAnimation {
                        from: 0.7
                        to: 0.1
                        duration: 1000
                    }
                }

                // Fade animation for indeterminate
                Behavior on width {
                    NumberAnimation {
                        duration: root.percentage === null ? 100 : 200
                        easing.type: Easing.InOutQuad
                    }
                }
            }
        }

        // Percentage label (if known)
        Text {
            visible: root.percentage !== null
            text: Math.round(root.percentage) + "%"
            color: textColor
            font.pixelSize: 11
            font.family: "monospace"
            Layout.alignment: Qt.AlignRight
        }
    }
}
