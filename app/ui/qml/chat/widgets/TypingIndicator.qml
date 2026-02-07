// TypingIndicator.qml - Animated typing indicator for streaming messages
import QtQuick 2.15
import QtQuick.Controls 2.15

Row {
    id: root

    property bool active: true
    property color dotColor: "#4a90e2"

    spacing: 6
    padding: 8

    implicitWidth: dotRow.implicitWidth + 16
    implicitHeight: 24

    // Opacity based on active state
    opacity: active ? 1.0 : 0.0

    Behavior on opacity {
        NumberAnimation { duration: 150 }
    }

    Row {
        id: dotRow
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        Repeater {
            model: 3

            delegate: Rectangle {
                width: 8
                height: 8
                radius: width / 2
                color: root.dotColor

                // Sequential animation for wave effect
                SequentialAnimation on opacity {
                    running: root.active
                    loops: Animation.Infinite
                    NumberAnimation {
                        to: 0.3
                        duration: 400
                    }
                    NumberAnimation {
                        to: 1.0
                        duration: 400
                    }
                    // Stagger each dot
                    PropertyAction { }
                }

                // Scale animation
                SequentialAnimation on scale {
                    running: root.active
                    loops: Animation.Infinite
                    NumberAnimation {
                        to: 0.8
                        duration: 400
                    }
                    NumberAnimation {
                        to: 1.0
                        duration: 400
                    }
                }

                // Stagger animations based on index
                Component.onCompleted: {
                    // Delay each dot's animation start
                    delayTimer.interval = index * 150
                    delayTimer.start()
                }

                Timer {
                    id: delayTimer
                    repeat: false
                    onTriggered: {
                        // Trigger initial animation state
                        parent.opacity = 0.5 + index * 0.2
                    }
                }
            }
        }
    }
}
