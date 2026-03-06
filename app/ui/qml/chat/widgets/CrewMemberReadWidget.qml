// CrewMemberReadWidget.qml - Display crew members who have read the message
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var data: ({})  // {content_type, data: {crew_members: [{id, name, icon, color}, ...]}}
    property color widgetColor: "#4a90e2"

    // Computed property for crew members list
    readonly property var crewMembers: {
        if (data && data.data && data.data.crew_members) {
            return data.data.crew_members
        }
        return []
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
                        text: modelData.icon || ""
                        font.pixelSize: 11
                    }

                    ToolTip.visible: toolTipMouseArea.containsMouse
                    ToolTip.delay: 400
                    ToolTip.timeout: 2000
                    ToolTip.text: modelData.name || ""

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

        // Read status text
        Text {
            text: "readed"
            color: "#707070"
            font.pixelSize: 11
            anchors.verticalCenter: row.verticalCenter
        }
    }
}