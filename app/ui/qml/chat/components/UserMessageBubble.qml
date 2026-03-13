// UserMessageBubble.qml - Right-aligned user message bubble with avatar
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

import "../widgets"

Item {
    id: root

    property string content: ""
    property bool isRead: true
    property string userName: "You"
    property string userIcon: "👤"
    property var structuredContent: []
    property string startTime: ""     // Formatted start time
    property string duration: ""      // Formatted duration (e.g., "2m 30s")
    property var crewReadBy: []       // List of crew members who read this message

    signal referenceClicked(string refType, string refId)

    // Theme colors
    readonly property color bubbleColor: "#4a90e2"
    readonly property color textColor: "#ffffff"
    readonly property color avatarColor: "#6fa8e8"
    readonly property color timeInfoColor: "#707070"
    readonly property int avatarSize: 32
    readonly property int avatarSpacing: 8
    readonly property int totalAvatarWidth: (avatarSize + avatarSpacing) * 2  // Both sides

    // Internal bubble padding
    readonly property int bubblePadding: 12
    readonly property int minBubbleWidth: 80
    readonly property int minContentWidth: 56  // minBubbleWidth - bubblePadding*2

    // Available width for bubble (total width minus avatar space on both sides)
    readonly property int availableWidth: Math.max(minBubbleWidth, width - totalAvatarWidth)
    // Max content area width (single source of truth; bubble width = this + 2*bubblePadding, capped by availableWidth)
    readonly property int maxContentWidth: Math.max(minContentWidth, availableWidth - bubblePadding * 2)

    // Pre-calculated content width from text measurement (matches MarkdownText font.pixelSize 14)
    property real preferredContentWidth: minContentWidth
    function _stripMarkdownForMeasure(s) {
        if (!s) return ""
        var t = s.replace(/\*\*/g, "").replace(/__/g, "").replace(/`/g, "")
        return t.replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")  // [text](url) -> text
    }
    function _measureTextWidth(text) {
        if (!text || !text.trim()) return minContentWidth
        var lines = _stripMarkdownForMeasure(text).split("\n")
        var maxW = minContentWidth
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i]
            if (line.length === 0) continue
            _textMetrics.text = line
            var w = _textMetrics.advanceWidth
            if (w > maxW) maxW = Math.ceil(w)
        }
        return maxW
    }
    function _updatePreferredContentWidth() {
        var textsToMeasure = []
        if (root.content && root.content.trim()) textsToMeasure.push(root.content)
        if (root.structuredContent && root.structuredContent.length > 0) {
            for (var j = 0; j < root.structuredContent.length; j++) {
                var item = root.structuredContent[j]
                var data = item.data || item
                if (data.text !== undefined && data.text) textsToMeasure.push(data.text)
            }
        }
        if (textsToMeasure.length === 0) {
            preferredContentWidth = Math.min(minContentWidth, root.maxContentWidth)
            return
        }
        var maxW = minContentWidth
        for (var k = 0; k < textsToMeasure.length; k++) {
            var w = _measureTextWidth(textsToMeasure[k])
            if (w > maxW) maxW = w
        }
        preferredContentWidth = Math.min(maxW, root.maxContentWidth)
    }
    onContentChanged: _updatePreferredContentWidth()
    onStructuredContentChanged: _updatePreferredContentWidth()
    onAvailableWidthChanged: _updatePreferredContentWidth()

    TextMetrics {
        id: _textMetrics
        font.pixelSize: 14
        font.weight: Font.Normal
    }

    implicitHeight: 12 + headerRow.height + 12 + bubbleContainer.height + 8 + (crewReadByRow.visible ? crewReadByRow.height + 4 : 0)

    // Header row - right aligned with time info, name, and avatar
    Row {
        id: headerRow
        anchors {
            right: parent.right
            rightMargin: 12
            top: parent.top
            topMargin: 12
        }
        spacing: 8
        height: Math.max(avatarRect.height, nameText.implicitHeight, timeInfoColumn.implicitHeight)

        // Time info column (before name)
        Column {
            id: timeInfoColumn
            spacing: 0
            anchors.verticalCenter: parent.verticalCenter
            visible: root.startTime !== "" || root.duration !== ""

            Text {
                text: root.startTime
                color: timeInfoColor
                font.pixelSize: 11
                font.weight: Font.Light
                visible: root.startTime !== ""
            }

            Text {
                text: root.duration
                color: timeInfoColor
                font.pixelSize: 10
                font.weight: Font.Light
                visible: root.duration !== ""
            }
        }

        // User name
        Text {
            id: nameText
            text: root.userName
            color: textColor
            font.pixelSize: 13
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
            opacity: 0.9
        }

        // Avatar/icon
        Rectangle {
            id: avatarRect
            width: avatarSize
            height: avatarSize
            radius: width / 2
            color: avatarColor
            anchors.verticalCenter: parent.verticalCenter

            Text {
                anchors.centerIn: parent
                text: root.userIcon
                font.pixelSize: 18
            }
        }
    }

    // Message bubble container positioned on the right
    Item {
        id: bubbleContainer
        anchors {
            right: parent.right
            rightMargin: avatarSize + avatarSpacing  // avatar space on the right side
            top: headerRow.bottom
            topMargin: 12
        }
        width: bubble.width
        height: bubble.height

        // Message bubble — width adapts to content, max = availableWidth
        Rectangle {
            id: bubble

            // Pre-calculated from TextMetrics (root.preferredContentWidth) + post-layout from children (explicitContentWidth); never exceed maxContentWidth
            property real explicitContentWidth: 0
            readonly property real calculatedContentWidth: Math.min(root.maxContentWidth, Math.max(root.preferredContentWidth, explicitContentWidth))

            width: Math.min(Math.max(root.minBubbleWidth, calculatedContentWidth + bubblePadding * 2), availableWidth)
            height: contentLoader.implicitHeight + bubblePadding * 2

            color: bubbleColor
            radius: 9

            // Structured content column - render through structured content
            StructuredContentRenderer {
                id: contentLoader
                anchors {
                    left: parent.left
                    top: parent.top
                    margins: bubblePadding
                }
                width: bubble.calculatedContentWidth
                structuredContent: root.structuredContent
                content: root.content
                textColor: root.textColor
                widgetColor: root.bubbleColor
                widgetSupport: "basic"
                onReferenceClicked: function(refType, refId) {
                    root.referenceClicked(refType, refId)
                }

                onImplicitHeightChanged: {
                    // Trigger bubble width recalculation when content changes
                    // Use restart() to debounce rapid height changes during content updates
                    calcWidthTimer.restart()
                }

                Timer {
                    id: calcWidthTimer
                    interval: 100  // Increased from 50ms to reduce frequency during rapid updates
                    onTriggered: {
                        if (contentLoader.children && contentLoader.children.length > 0) {
                            var maxW = root.minContentWidth
                            // contentLoader.children[0] is the contentColumn
                            var contentColumn = contentLoader.children[0]
                            if (contentColumn && contentColumn.children) {
                                for (var i = 0; i < contentColumn.children.length; i++) {
                                    var child = contentColumn.children[i]
                                    // For Loaders, check their item's implicitWidth
                                    if (child.item && child.item.implicitWidth !== undefined) {
                                        var w = child.item.implicitWidth
                                        if (w > maxW) maxW = w
                                    }
                                    // Also check the Loader's own implicitWidth
                                    else if (child.implicitWidth !== undefined) {
                                        var w = child.implicitWidth
                                        if (w > maxW) maxW = w
                                    }
                                }
                            }
                            bubble.explicitContentWidth = Math.min(root.maxContentWidth, Math.max(root.minContentWidth, maxW))
                        }
                    }
                }
            }
        }
    }

    // Crew read-by indicator (shows which crew members have read this message)
    Row {
        id: crewReadByRow
        anchors {
            right: parent.right
            rightMargin: avatarSize + avatarSpacing
            top: bubbleContainer.bottom
            topMargin: 4
        }
        spacing: 4
        visible: root.crewReadBy && root.crewReadBy.length > 0

        Repeater {
            model: root.crewReadBy || []

            Rectangle {
                id: avatarRect
                width: 20
                height: 20
                radius: width / 2
                color: modelData.color || "#4a90e2"

                Text {
                    anchors.centerIn: parent
                    text: modelData.icon || "🤖"
                    font.pixelSize: 10
                }

                MouseArea {
                    id: avatarMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                }

                ToolTip {
                    text: modelData.name || ""
                    visible: avatarMouseArea.containsMouse
                }
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: (root.crewReadBy || []).length + " 人已读"
            color: timeInfoColor
            font.pixelSize: 10
            visible: (root.crewReadBy || []).length > 0
        }
    }
}
