// CrewMemberActivityWidget.qml - Display crew members who are currently thinking/typing
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var data: ({})  // {content_type, data: {crew_members: [{id, name, icon, color}, ...]}}
    property color widgetColor: "#4a90e2"

    // Crew members list, updated when data changes
    property var crewMembers: []

    onDataChanged: {
        if (data && data.data && Array.isArray(data.data.crew_members)) {
            crewMembers = data.data.crew_members
        } else {
            crewMembers = []
        }
    }

    implicitWidth: row.implicitWidth
    implicitHeight: row.implicitHeight

    Row {
        id: row
        spacing: 8
        anchors.centerIn: parent

        // Crew member avatars row
        Row {
            spacing: -6

            Repeater {
                model: root.crewMembers

                Rectangle {
                    width: 24
                    height: 24
                    radius: 12
                    color: modelData.color || "#5a6a7a"
                    border.width: 2
                    border.color: root.widgetColor
                    z: index

                    Text {
                        anchors.centerIn: parent
                        text: modelData.icon || (modelData.name ? modelData.name[0].toUpperCase() : "?")
                        font.pixelSize: 11
                        color: "#ffffff"
                    }

                    ToolTip.visible: toolTipMouseArea.containsMouse
                    ToolTip.delay: 400
                    ToolTip.timeout: 2000
                    ToolTip.text: modelData.name || "Unknown"

                    MouseArea {
                        id: toolTipMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                    }
                }
            }
        }

        // Separator line
        Rectangle {
            width: 1
            height: 18
            color: "#505050"
            anchors.verticalCenter: row.verticalCenter
        }

        // Animated bouncing dots (thinking indicator)
        Row {
            spacing: 4
            anchors.verticalCenter: row.verticalCenter

            Repeater {
                model: 3

                Rectangle {
                    width: 6
                    height: 6
                    radius: 3
                    color: root.widgetColor

                    property int dotIndex: index

                    SequentialAnimation on opacity {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.3; duration: 350 }
                        NumberAnimation { to: 1.0; duration: 350 }
                    }

                    SequentialAnimation on scale {
                        running: true
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.6; duration: 350 }
                        NumberAnimation { to: 1.0; duration: 350 }
                    }

                    Component.onCompleted: {
                        opacity = 0.4 + dotIndex * 0.25
                    }
                }
            }
        }

        // Thinking status text
        Text {
            text: "thinking..."
            color: "#707070"
            font.pixelSize: 11
            anchors.verticalCenter: row.verticalCenter
        }
    }
}