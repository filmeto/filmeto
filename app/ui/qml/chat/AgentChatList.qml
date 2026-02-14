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
    signal scrollPositionChanged(bool atBottom)

    // Configuration
    width: 400
    height: 600
    spacing: 12

    // Loading state property (set from Python)
    property bool isLoadingOlder: false

    // Model from Python (via contextProperty)
    model: _chatModel

    // Smooth scrolling
    flickableDirection: Flickable.VerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    // Cache 3x viewport height above/below for smoother scrolling with complex delegates.
    // Increased from 2x to 3x to pre-render more delegates and reduce pop-in during fast scrolling.
    cacheBuffer: height * 3
    clip: true

    // Bottom margin to ensure last message is fully visible
    bottomMargin: 32

    // Track if user is at bottom (within threshold pixels)
    readonly property int bottomThreshold: 50
    readonly property bool isAtBottom: contentHeight - contentY - height < bottomThreshold

    // Notify Python when scroll position changes
    onContentYChanged: {
        scrollPositionChanged(isAtBottom)
    }
    onHeightChanged: {
        scrollPositionChanged(isAtBottom)
    }
    onContentHeightChanged: {
        scrollPositionChanged(isAtBottom)
    }

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

    // Loading indicator at top (shown when loading older messages)
    Item {
        id: loadingIndicator
        anchors.top: parent.top
        width: parent.width
        height: 40
        visible: root.isLoadingOlder
        z: 10

        Rectangle {
            anchors.fill: parent
            color: "#252525"
            opacity: 0.9
        }

        Row {
            anchors.centerIn: parent
            spacing: 8

            BusyIndicator {
                width: 20
                height: 20
                running: root.isLoadingOlder
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "Loading older messages..."
                color: "#888888"
                font.pixelSize: 13
            }
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

    // Public method to position view at a specific index
    // mode: 0 = Center, 1 = Beginning, 2 = End
    function positionViewAtIndex(index, mode) {
        positionViewAtIndex(index, mode)
    }
}
