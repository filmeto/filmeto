import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import ".." as Chat

Item {
    id: root

    property var chatModel: null
    property var planViewModel: null

    signal loadMoreRequested()
    signal referenceClicked(string refType, string refId)
    signal messageCompleted(string messageId, string agentName)

    anchors.fill: parent

    SplitView {
        id: splitView
        anchors.fill: parent
        orientation: Qt.Vertical
        handle: Item { implicitHeight: 0 }

        Chat.AgentChatList {
            id: chatList
            objectName: "agentChatList"
            SplitView.fillWidth: true
            SplitView.fillHeight: true
            chatModel: root.chatModel

            onLoadMoreRequested: root.loadMoreRequested()
            onReferenceClicked: root.referenceClicked(refType, refId)
            onMessageCompleted: root.messageCompleted(messageId, agentName)
        }

        PlanWidget {
            id: planWidget
            objectName: "agentChatPlan"
            SplitView.fillWidth: true

            mode: "panel"
            planViewModel: root.planViewModel
            planBridge: root.planViewModel

            // Keep deterministic heights (similar to legacy splitter integration).
            SplitView.preferredHeight: isExpanded ? 352 : 52
            SplitView.minimumHeight: isExpanded ? 352 : 52
            SplitView.maximumHeight: isExpanded ? 352 : 52
        }
    }
}

