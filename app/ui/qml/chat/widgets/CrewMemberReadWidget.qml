// CrewMemberReadWidget.qml - Display crew members who have read the message
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Row {
    id: root

    property var data: ({})  // {content_type, data: {crew_members: [{id, name, icon, color}, ...]}}
    property color widgetColor: "#4a90e2"

    spacing: 8
    height: 24  // Set explicit height for proper vertical centering

    // Crew member avatars row
    Row {
        id: avatarRow
        spacing: -6
        height: parent.height

        Repeater {
            model: (root.data.data && root.data.data.crew_members) ? root.data.data.crew_members : []

            Rectangle {
                width: 24
                height: 24
                radius: 12
                color: (modelData && modelData.color) ? modelData.color : "#5a6a7a"
                border.width: 2
                border.color: root.widgetColor
                z: model.index

                Text {
                    anchors.centerIn: parent
                    text: (modelData && modelData.icon) ? modelData.icon : ""
                    font.pixelSize: 11
                }

                ToolTip.visible: toolTipMouseArea.containsMouse
                ToolTip.delay: 400
                ToolTip.timeout: 2000
                ToolTip.text: (modelData && modelData.name) ? modelData.name : ""

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
        anchors.verticalCenter: parent.verticalCenter
        color: "#505050"
    }

    // Read status text
    Text {
        text: "readed"
        color: "#707070"
        font.pixelSize: 11
        anchors.verticalCenter: parent.verticalCenter
    }
}