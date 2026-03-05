// AgentMessageBubble.qml - Left-aligned agent message with avatar and metadata
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

Item {
    id: root

    property string senderName: ""
    property string content: ""
    property color agentColor: "#4a90e2"
    property string agentIcon: "🤖"
    property var crewMetadata: ({})
    property var structuredContent: []
    property string startTime: ""     // Formatted start time (HH:MM)
    property string duration: ""      // Formatted duration (e.g., "2m 30s")

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color backgroundColor: "#353535"
    readonly property color textColor: "#e0e0e0"
    readonly property color nameColor: agentColor
    readonly property color timestampColor: "#808080"
    readonly property color timeInfoColor: "#707070"

    // Avatar dimensions
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Available width for content (minus avatar space on both sides)
    readonly property int availableWidth: parent.width - totalAvatarWidth

    // Width is determined by anchors, height is calculated dynamically
    implicitHeight: headerRow.height + contentRect.implicitHeight + 8

    // Header row with avatar, name (left) and time info (right)
    Row {
        id: headerRow
        anchors {
            left: parent.left
            leftMargin: 12
            right: parent.right
            rightMargin: 12
            top: parent.top
            topMargin: 12
        }
        spacing: 8
        height: Math.max(avatarRect.height, nameColumn.implicitHeight, timeInfoColumn.implicitHeight)

        // Avatar/icon
        Rectangle {
            id: avatarRect
            width: 32
            height: 32
            radius: width / 2
            color: root.agentColor
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.agentIcon
                font.pixelSize: 18
            }
        }

        // Agent name and title column (left side)
        Column {
            id: nameColumn
            spacing: 4
            anchors.verticalCenter: parent.verticalCenter

            Text {
                text: root.senderName
                color: nameColor
                font.pixelSize: 13
                font.weight: Font.Medium
            }

            // Crew title color block if available
            Rectangle {
                id: crewTitleBlock
                visible: root.crewMetadata !== undefined && root.crewMetadata.crew_title_display !== undefined && root.crewMetadata.crew_title_display !== ""
                width: crewTitleText.implicitWidth + 16
                height: 18
                color: root.agentColor
                radius: 3

                Text {
                    id: crewTitleText
                    anchors.centerIn: parent
                    text: (root.crewMetadata && root.crewMetadata.crew_title_display) || ""
                    color: "#ffffff"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                }
            }
        }

        // Spacer to push time info to the right
        Item {
            Layout.fillWidth: true
            width: 1  // Minimum width
        }

        // Time info column (right side)
        Column {
            id: timeInfoColumn
            spacing: 2
            anchors.verticalCenter: parent.verticalCenter
            visible: root.startTime !== "" || root.duration !== ""

            Text {
                id: startTimeText
                text: root.startTime
                color: timeInfoColor
                font.pixelSize: 11
                font.weight: Font.Light
                horizontalAlignment: Text.AlignRight
                anchors.right: parent.right
                visible: root.startTime !== ""
            }

            Text {
                id: durationText
                text: root.duration
                color: timeInfoColor
                font.pixelSize: 10
                font.weight: Font.Light
                horizontalAlignment: Text.AlignRight
                anchors.right: parent.right
                visible: root.duration !== ""
            }
        }
    }

    // Message content area - aligned with avatar
    Rectangle {
        id: contentRect
        anchors {
            left: parent.left
            leftMargin: 40  // avatar (32) + spacing (8)
            top: headerRow.bottom
            topMargin: 12
        }
        width: availableWidth
        implicitHeight: contentRenderer.implicitHeight + 24
        color: backgroundColor
        radius: 6

        // Content column - render through structured content
        StructuredContentRenderer {
            id: contentRenderer
            anchors {
                left: parent.left
                top: parent.top
                margins: 12
            }
            width: parent.width - 24
            structuredContent: root.structuredContent
            content: root.content
            textColor: root.textColor
            widgetColor: root.agentColor
            widgetSupport: "full"
            onReferenceClicked: function(refType, refId) {
                root.referenceClicked(refType, refId)
            }
        }
    }
}
