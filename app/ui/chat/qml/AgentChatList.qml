// AgentChatList.qml - Complete implementation using existing bubble components
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "./components"  // Import components subdirectory for bubble components

ListView {
    id: root

    // Utility function for formatting timestamps
    function formatTimestamp(timestamp) {
        if (!timestamp) return ""

        var date = new Date(timestamp)
        var now = new Date()

        // Check if date is valid
        if (isNaN(date.getTime())) return ""

        // Get date components
        var hours = date.getHours().toString().padStart(2, '0')
        var minutes = date.getMinutes().toString().padStart(2, '0')
        var seconds = date.getSeconds().toString().padStart(2, '0')
        var day = date.getDate().toString().padStart(2, '0')
        var month = (date.getMonth() + 1).toString().padStart(2, '0')
        var year = date.getFullYear()

        var timeStr = hours + ":" + minutes + ":" + seconds

        // Same day: show "HH:mm:ss"
        if (date.toDateString() === now.toDateString()) {
            return timeStr
        }

        // Same month: show "DD HH:mm:ss"
        if (date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear()) {
            return day + " " + timeStr
        }

        // Same year: show "MM-DD HH:mm:ss"
        if (date.getFullYear() === now.getFullYear()) {
            return month + "-" + day + " " + timeStr
        }

        // Older: show "YYYY-MM-DD HH:mm:ss"
        return year + "-" + month + "-" + day + " " + timeStr
    }

    // Signals
    signal loadMoreRequested()
    signal referenceClicked(string refType, string refId)
    signal messageCompleted(string messageId, string agentName)

    // Configuration
    width: 400
    height: 600
    spacing: 12

    // Model from Python (via contextProperty)
    model: _chatModel

    // Smooth scrolling
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    cacheBuffer: height * 2
    clip: true

    // Bottom margin to ensure last message is fully visible
    bottomMargin: 32

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#252525"
        z: -1
    }

    // Scrollbar width
    readonly property int scrollbarWidth: 10

    // Main delegate - use Loader to select component
    delegate: Loader {
        id: loader
        width: root.width - root.scrollbarWidth

        // Expose model data to loaded component
        property var modelData: model

        // Determine which component to load
        sourceComponent: (modelData.isUser || false) ? userComponent : agentComponent

        // User message component
        Component {
            id: userComponent

            UserMessageBubble {
                anchors {
                    right: parent.right
                    left: parent.left
                }
                isRead: modelData.isRead !== undefined ? modelData.isRead : true
                userName: modelData.userName || "You"
                userIcon: modelData.userIcon || "👤"
                timestamp: root.formatTimestamp(modelData.timestamp || "")
                structuredContent: modelData.structuredContent || []
            }
        }

        // Agent message component
        Component {
            id: agentComponent

            AgentMessageBubble {
                anchors {
                    left: parent.left
                    right: parent.right
                }
                senderName: modelData.senderName || ""
                agentColor: modelData.agentColor || "#4a90e2"
                agentIcon: modelData.agentIcon || "🤖"
                crewMetadata: modelData.crewMetadata || {}
                structuredContent: modelData.structuredContent || []
                timestamp: root.formatTimestamp(modelData.timestamp || "")

                onReferenceClicked: function(refType, refId) {
                    root.referenceClicked(refType, refId)
                }
            }
        }
    }

    // Scrollbar
    ScrollBar.vertical: ScrollBar {
        policy: ScrollBar.AsNeeded
        contentItem: Rectangle {
            implicitWidth: 10
            radius: width / 2
            color: parent.pressed ? "#606264" :
                   parent.hovered ? "#606264" : "#505254"
            opacity: parent.active ? 1.0 : 0.5

            Behavior on opacity {
                NumberAnimation { duration: 150 }
            }
        }
        background: Rectangle {
            color: "#2b2d30"
            implicitWidth: 10
        }
    }

    // Load more trigger at top
    onAtYBeginningChanged: {
        if (atYBeginning) {
            root.loadMoreRequested()
        }
    }

    // Public method to scroll to bottom
    function scrollToBottom() {
        positionViewAtEnd()
    }
}
