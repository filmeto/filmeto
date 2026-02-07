// AgentChatList.qml - Complete implementation using existing bubble components
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "."  // Import current directory for components

ListView {
    id: root

    // Signals
    signal loadMoreRequested()
    signal referenceClicked(string refType, string refId)
    signal messageCompleted(string messageId, string agentName)

    // Configuration
    width: 400
    height: 600
    spacing: 12

    // Content margins - 12px gap from outer container
    leftMargin: 12
    rightMargin: 12
    topMargin: 12
    bottomMargin: 12

    // Model from Python (via contextProperty)
    model: _chatModel

    // Smooth scrolling
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    cacheBuffer: height * 2
    clip: true

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#252525"
        z: -1
    }

    // Main delegate - use Loader to select component
    delegate: Loader {
        id: loader
        width: root.width - root.leftMargin - root.rightMargin

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
                content: modelData.content || ""
                isRead: modelData.isRead !== undefined ? modelData.isRead : true
                userName: modelData.userName || "You"
                userIcon: modelData.userIcon || "👤"
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
                content: modelData.content || ""
                agentColor: modelData.agentColor || "#4a90e2"
                agentIcon: modelData.agentIcon || "🤖"
                crewMetadata: modelData.crewMetadata || {}
                structuredContent: modelData.structuredContent || []

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
