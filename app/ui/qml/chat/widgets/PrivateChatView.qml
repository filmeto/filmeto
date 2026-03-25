import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import ".." as Chat

Item {
    id: root

    property var chatModel: null
    property string title: ""

    signal loadMoreRequested()
    signal referenceClicked(string refType, string refId)
    signal messageCompleted(string messageId, string agentName)

    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Optional header (kept simple; no business logic).
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: title.length > 0 ? 34 : 0
            visible: title.length > 0
            color: "#2b2d30"
            border.color: "#3a3a3a"
            border.width: 1

            Text {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 10
                text: root.title
                color: "#e1e1e1"
                font.pixelSize: 12
                elide: Text.ElideRight
                width: parent.width - 20
            }
        }

        SplitView {
            id: splitView
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Vertical
            handle: Item { implicitHeight: 0 }

            Chat.AgentChatList {
                id: chatList
                objectName: "privateChatList"
                SplitView.fillWidth: true
                SplitView.fillHeight: true
                chatModel: root.chatModel

                onLoadMoreRequested: root.loadMoreRequested()
                onReferenceClicked: root.referenceClicked(refType, refId)
                onMessageCompleted: root.messageCompleted(messageId, agentName)
            }
        }
    }
}

