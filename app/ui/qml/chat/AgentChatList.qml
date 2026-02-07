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
        width: root.width

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
                    rightMargin: 52  // avatar (32) + spacing (8) + extra padding (12)
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
                    leftMargin: 12
                    right: parent.right
                    rightMargin: 12
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
