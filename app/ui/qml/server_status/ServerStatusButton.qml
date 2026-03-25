import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    width: 100
    height: 32

    property url iconFontSource: ""
    property var viewState: null

    FontLoader {
        id: iconFontLoader
        source: root.iconFontSource
    }

    readonly property string iconFamily: {
        if (iconFontLoader.status === FontLoader.Ready && iconFontLoader.name.length > 0)
            return iconFontLoader.name
        return "iconfont"
    }

    readonly property int totalCount: viewState ? (viewState.activeCount + viewState.inactiveCount) : 0
    readonly property color badgeFill: {
        if (totalCount <= 0)
            return "#808080"
        return viewState.activeCount > 0 ? "#4CAF50" : "#F44336"
    }
    readonly property bool showBadgeNumber: totalCount > 0
    readonly property string badgeLabel: totalCount >= 100 ? "99+" : String(totalCount)

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: 6
        // Match settings button style: transparent normally, rgba(255,255,255,0.1) on hover
        color: mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.1) : "transparent"
        // No border (match settings button)
        border.width: 0
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: 4

        Text {
            text: "\ue66e"
            font.family: root.iconFamily
            font.pixelSize: 18
            // Match settings button: #888888 normal, #E1E1E1 hover
            color: mouseArea.containsMouse ? "#E1E1E1" : "#888888"
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: "Server"
            font.pixelSize: 12
            // Match settings button: #888888 normal, #E1E1E1 hover
            color: mouseArea.containsMouse ? "#E1E1E1" : "#888888"
            Layout.alignment: Qt.AlignVCenter
        }

        Item {
            Layout.fillWidth: true
        }

        Item {
            id: badgeHost
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Layout.alignment: Qt.AlignVCenter | Qt.AlignRight

            Rectangle {
                anchors.centerIn: parent
                width: 18
                height: 18
                radius: 9
                color: root.badgeFill
            }

            Text {
                anchors.centerIn: parent
                visible: root.showBadgeNumber
                text: root.badgeLabel
                font.family: "Arial"
                font.pixelSize: 10
                font.bold: true
                color: "#ffffff"
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (viewState)
                viewState.click()
        }
    }
}
