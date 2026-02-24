// StructuredContentRenderer.qml - Reusable component for rendering structured message content
//
// Content is divided into two sections:
// 1. Content section (top, flat): text, code_block, image, video, audio,
//    link, button, form, file, file_attachment, todo_write
// 2. Thinking section (bottom, collapsible): all other types
//
// The thinking section shows animated bouncing dots while streaming
// and a static thinking icon when the message is complete.
//
// PERFORMANCE NOTE: The Repeaters use count-based models (integer) instead of JS arrays.
// When the model is a JS array, QML's Repeater destroys ALL delegates and recreates them
// whenever the array property re-evaluates (which creates a new JS array object).
// With a count-based model, the Repeater only creates/destroys delegates when the count
// actually changes.
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // Input data
    property var structuredContent: []
    property string content: ""

    // Styling
    property color textColor: "#e0e0e0"
    property color widgetColor: "#4a90e2"

    // Widget type support: "full" for all widgets, "basic" for user messages
    property string widgetSupport: "full"

    // Signals
    signal referenceClicked(string refType, string refId)

    implicitHeight: contentColumn.height

    // Content types that display as main content (flat, top section)
    readonly property var _mainContentTypes: [
        "text", "code_block", "image", "video", "audio",
        "link", "button", "form", "file", "file_attachment", "todo_write"
    ]

    // Helper to check if a type is main content
    function _isMainContentType(type) {
        return _mainContentTypes.indexOf(type) >= 0
    }

    // Effective structured content (fallback to text if no structured content)
    property var effectiveStructuredContent: {
        if (root.structuredContent && root.structuredContent.length > 0) {
            return root.structuredContent
        }
        return [{ content_type: "text", text: root.content || "" }]
    }

    // Main content items (displayed flat in content section)
    property var mainContentItems: {
        if (widgetSupport !== "full") {
            return effectiveStructuredContent
        }
        var items = []
        for (var i = 0; i < effectiveStructuredContent.length; i++) {
            var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
            if (type !== "typing" && root._isMainContentType(type)) {
                items.push(effectiveStructuredContent[i])
            }
        }
        return items
    }

    // Thinking process items (displayed in collapsible section)
    property var thinkingItems: {
        if (widgetSupport !== "full") return []
        var items = []
        for (var i = 0; i < effectiveStructuredContent.length; i++) {
            var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
            if (type !== "typing" && !root._isMainContentType(type)) {
                items.push(effectiveStructuredContent[i])
            }
        }
        return items
    }

    // Typing content (presence indicates streaming state)
    // Only includes typing with state="start", not state="end"
    property var typingContent: {
        if (widgetSupport !== "full") return []
        var items = []
        for (var i = 0; i < effectiveStructuredContent.length; i++) {
            var type = effectiveStructuredContent[i].content_type || effectiveStructuredContent[i].type || "text"
            if (type === "typing") {
                // Only include typing content with state="start"
                // state="end" is kept in history but doesn't trigger streaming state
                var data = effectiveStructuredContent[i].data || {}
                var state = data.state || "start"
                if (state === "start") {
                    items.push(effectiveStructuredContent[i])
                }
            }
        }
        return items
    }

    // Whether message is still streaming
    readonly property bool isStreaming: typingContent.length > 0

    // Whether thinking section should be visible
    readonly property bool hasThinkingSection: (thinkingItems.length > 0 || isStreaming) && widgetSupport === "full"

    // Thinking section expanded/collapsed state
    property bool thinkingExpanded: false

    // Live summary of the latest thinking item for collapsed-state display
    readonly property string _latestThinkingSummary: {
        var items = root.thinkingItems
        if (items.length > 0) {
            var latest = items[items.length - 1]
            var type = latest.content_type || latest.type || ""
            var data = latest.data || {}
            switch (type) {
                case "thinking":
                    var thought = data.thought || latest.thought || ""
                    return thought ? thought.replace(/\n/g, " ") : ""
                case "tool_call":
                    var tn = data.tool_name || latest.tool_name || ""
                    var st = data.status || latest.status || ""
                    if (tn) {
                        if (st === "started" || st === "running")
                            return "🔧 " + tn + "..."
                        if (st === "completed" || st === "success")
                            return "🔧 " + tn + " ✓"
                        if (st === "error" || st === "failed")
                            return "🔧 " + tn + " ✗"
                        return "🔧 " + tn
                    }
                    return ""
                case "tool_response":
                    return "📋 " + (data.tool_name || latest.tool_name || "Response")
                case "skill":
                    return "⚡ " + (data.name || latest.title || "Skill")
                case "step":
                    return latest.title || data.title || ""
                case "plan":
                    return "📋 " + (latest.title || "Plan")
                case "progress":
                    return data.progress || latest.progress || ""
                case "llm_output":
                    return "💬 " + (latest.title || data.title || "LLM Output")
                case "error":
                    return "❌ " + (data.error || latest.title || "Error")
                case "metadata":
                    return latest.title || data.metadata_type || ""
                default:
                    return latest.title || latest.description || type
            }
        }
        if (root.isStreaming) {
            var mainItems = root.mainContentItems
            if (mainItems.length > 0) {
                var latestMain = mainItems[mainItems.length - 1]
                var mainType = latestMain.content_type || latestMain.type || "text"
                switch (mainType) {
                    case "text": return "Generating text..."
                    case "code_block": return "Generating code..."
                    case "image": return "Processing image..."
                    case "video": return "Processing video..."
                    case "audio": return "Processing audio..."
                    case "file":
                    case "file_attachment": return "Processing file..."
                    case "todo_write": return "Writing tasks..."
                    default: return ""
                }
            }
        }
        return ""
    }

    // Helper: resolve the correct Component for a content type string
    function _resolveComponent(type) {
        switch (type) {
            // Basic content
            case "text": return textWidgetComponent
            case "code_block": return codeBlockComponent

            // Thinking content (full support only)
            case "thinking": return widgetSupport === "full" ? thinkingWidgetComponent : textWidgetComponent

            // Tool content (full support only)
            case "tool_call": return widgetSupport === "full" ? toolCallComponent : textWidgetComponent
            case "tool_response": return widgetSupport === "full" ? toolResponseComponent : textWidgetComponent

            // Media content
            case "image": return imageWidgetComponent
            case "video": return widgetSupport === "full" ? videoWidgetComponent : textWidgetComponent
            case "audio": return widgetSupport === "full" ? audioWidgetComponent : textWidgetComponent

            // Data display (full support only)
            case "table": return widgetSupport === "full" ? tableWidgetComponent : textWidgetComponent
            case "chart": return widgetSupport === "full" ? chartWidgetComponent : textWidgetComponent

            // Interactive elements
            case "link": return linkWidgetComponent
            case "button": return widgetSupport === "full" ? buttonWidgetComponent : textWidgetComponent
            case "form": return widgetSupport === "full" ? formWidgetComponent : textWidgetComponent

            // Files
            case "file_attachment":
            case "file": return fileWidgetComponent

            // Tasks and plans (full support only)
            case "plan": return widgetSupport === "full" ? planWidgetComponent : textWidgetComponent
            case "task_list":
            case "task": return widgetSupport === "full" ? taskWidgetComponent : textWidgetComponent
            case "step": return widgetSupport === "full" ? stepWidgetComponent : textWidgetComponent
            case "skill": return widgetSupport === "full" ? skillWidgetComponent : textWidgetComponent

            // Status and metadata (full support only)
            case "progress": return widgetSupport === "full" ? progressWidgetComponent : textWidgetComponent
            case "todo_write": return widgetSupport === "full" ? todoWriteWidgetComponent : textWidgetComponent
            case "metadata": return widgetSupport === "full" ? metadataWidgetComponent : textWidgetComponent
            case "error": return widgetSupport === "full" ? errorWidgetComponent : textWidgetComponent
            case "llm_output": return widgetSupport === "full" ? llmOutputComponent : textWidgetComponent

            default: return textWidgetComponent
        }
    }

    Column {
        id: contentColumn
        spacing: 8
        width: parent.width

        // ─── Content Section (flat display, always visible) ─────────
        Repeater {
            model: mainContentItems.length

            delegate: Loader {
                id: mainWidgetLoader
                width: contentColumn.width

                property var widgetData: root.mainContentItems[index] || ({})
                property var loadedItem: null

                sourceComponent: root._resolveComponent(
                    widgetData.content_type || widgetData.type || "text"
                )

                onLoaded: {
                    loadedItem = item
                    _applyDataToItem()
                }

                onWidgetDataChanged: {
                    if (loadedItem) {
                        _applyDataToItem()
                    }
                }

                function _applyDataToItem() {
                    if (loadedItem.hasOwnProperty('data')) {
                        loadedItem.data = widgetData
                    }
                    if (loadedItem.hasOwnProperty('widgetColor')) {
                        loadedItem.widgetColor = root.widgetColor
                    }
                }

                height: loadedItem ? (loadedItem.implicitHeight || loadedItem.height || 0) : 0
            }
        }

        // ─── Thinking Section (collapsible, below content) ──────────
        Item {
            id: thinkingSection
            visible: root.hasThinkingSection
            width: contentColumn.width
            height: visible ? thinkingSectionCol.height : 0

            Column {
                id: thinkingSectionCol
                width: parent.width
                spacing: 0

                // Thinking header bar
                Rectangle {
                    id: thinkingHeaderBar
                    width: parent.width
                    height: 34
                    radius: root.thinkingExpanded ? 8 : 17
                    color: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.08)
                    border.color: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.15)
                    border.width: 1

                    Behavior on radius {
                        NumberAnimation { duration: 150; easing.type: Easing.InOutQuad }
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        spacing: 6

                        // Animated bouncing dots (shown while streaming)
                        Row {
                            id: bouncingDotsRow
                            spacing: 4
                            visible: root.isStreaming
                            Layout.alignment: Qt.AlignVCenter

                            Repeater {
                                model: 3

                                delegate: Rectangle {
                                    id: dot
                                    width: 6
                                    height: 6
                                    radius: 3
                                    color: root.widgetColor
                                    anchors.verticalCenter: parent.verticalCenter

                                    property int dotIndex: index

                                    SequentialAnimation on opacity {
                                        running: root.isStreaming && bouncingDotsRow.visible
                                        loops: Animation.Infinite
                                        NumberAnimation { to: 0.3; duration: 350 }
                                        NumberAnimation { to: 1.0; duration: 350 }
                                    }

                                    SequentialAnimation on scale {
                                        running: root.isStreaming && bouncingDotsRow.visible
                                        loops: Animation.Infinite
                                        NumberAnimation { to: 0.6; duration: 350 }
                                        NumberAnimation { to: 1.0; duration: 350 }
                                    }

                                    Component.onCompleted: {
                                        opacity = 0.4 + dotIndex * 0.25
                                    }
                                }
                            }
                        }

                        // Static thinking icon (shown when finished)
                        Text {
                            id: thinkingIcon
                            text: "💭"
                            font.pixelSize: 14
                            visible: !root.isStreaming
                            Layout.alignment: Qt.AlignVCenter
                        }

                        // Label text
                        Text {
                            text: {
                                if (root.isStreaming) {
                                    return root.thinkingItems.length > 0
                                        ? "Thinking (" + root.thinkingItems.length + ")"
                                        : "Thinking..."
                                }
                                var count = root.thinkingItems.length
                                return count > 0
                                    ? "Thinking Process (" + count + ")"
                                    : "Thinking Process"
                            }
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.5)
                            font.pixelSize: 12
                            Layout.alignment: Qt.AlignVCenter
                        }

                        // Separator dot (when there's summary text)
                        Text {
                            visible: thinkingSummaryText.text.length > 0
                            text: "·"
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.3)
                            font.pixelSize: 12
                            font.bold: true
                            Layout.alignment: Qt.AlignVCenter
                        }

                        // Live summary of current thinking activity
                        Text {
                            id: thinkingSummaryText
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            text: root._latestThinkingSummary
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.38)
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }

                        // Expand/collapse arrow (only when there are items)
                        Text {
                            visible: root.thinkingItems.length > 0
                            text: root.thinkingExpanded ? "▲" : "▼"
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.4)
                            font.pixelSize: 9
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: root.thinkingItems.length > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (root.thinkingItems.length > 0) {
                                root.thinkingExpanded = !root.thinkingExpanded
                            }
                        }
                    }
                }

                // Expanded thinking content area
                Rectangle {
                    id: thinkingContentArea
                    visible: root.thinkingExpanded && root.thinkingItems.length > 0
                    width: parent.width
                    height: visible ? thinkingContentCol.height + 16 : 0
                    color: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.04)
                    border.color: Qt.rgba(root.widgetColor.r, root.widgetColor.g, root.widgetColor.b, 0.1)
                    border.width: 1
                    radius: 8

                    Behavior on height {
                        NumberAnimation { duration: 200; easing.type: Easing.InOutQuad }
                    }

                    Column {
                        id: thinkingContentCol
                        anchors {
                            left: parent.left
                            right: parent.right
                            top: parent.top
                            margins: 8
                        }
                        spacing: 8

                        Repeater {
                            model: root.thinkingItems.length

                            delegate: Loader {
                                id: thinkingWidgetLoader
                                width: thinkingContentCol.width

                                property var widgetData: root.thinkingItems[index] || ({})
                                property var loadedItem: null

                                sourceComponent: root._resolveComponent(
                                    widgetData.content_type || widgetData.type || "text"
                                )

                                onLoaded: {
                                    loadedItem = item
                                    _applyDataToItem()
                                }

                                onWidgetDataChanged: {
                                    if (loadedItem) {
                                        _applyDataToItem()
                                    }
                                }

                                function _applyDataToItem() {
                                    if (loadedItem.hasOwnProperty('data')) {
                                        loadedItem.data = widgetData
                                    }
                                    if (loadedItem.hasOwnProperty('widgetColor')) {
                                        loadedItem.widgetColor = root.widgetColor
                                    }
                                }

                                height: loadedItem ? (loadedItem.implicitHeight || loadedItem.height || 0) : 0
                            }
                        }
                    }
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // Widget Components
    // ─────────────────────────────────────────────────────────────

    // Text widget
    Component {
        id: textWidgetComponent

        Text {
            property var data: ({})
            text: data.text || data.data?.text || ""
            color: textColor
            font.pixelSize: 14
            wrapMode: Text.WordWrap
            textFormat: Text.PlainText
            lineHeight: widgetSupport === "full" ? 1.5 : 1.4
            linkColor: "#87ceeb"
            width: parent.width

            onLinkActivated: function(link) {
                if (link.startsWith("ref://")) {
                    var parts = link.substring(6).split(":")
                    if (parts.length >= 2) {
                        root.referenceClicked(parts[0], parts[1])
                    }
                } else {
                    Qt.openUrlExternally(link)
                }
            }
        }
    }

    // Code block widget
    Component {
        id: codeBlockComponent

        CodeBlockWidget {
            property var data: ({})
            width: parent.width
            code: data.code || data.data?.code || ""
            language: data.language || data.data?.language || "text"
        }
    }

    // Thinking widget (collapsible)
    Component {
        id: thinkingWidgetComponent

        ThinkingWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            thought: data.thought || data.data?.thought || ""
            title: data.title || data.data?.title || "Thinking Process"
            isCollapsible: true
        }
    }

    // Tool call widget
    Component {
        id: toolCallComponent

        ToolCallWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            toolName: data.tool_name || data.data?.tool_name || ""
            toolArgs: data.tool_args || data.data?.tool_args || data.tool_input || data.data?.tool_input || {}
            toolStatus: data.status || data.data?.status || "started"
            result: data.result !== undefined ? data.result : (data.data?.result !== undefined ? data.data.result : null)
            error: data.error || data.data?.error || ""
        }
    }

    // Tool response widget
    Component {
        id: toolResponseComponent

        ToolResponseWidget {
            property var data: ({})
            width: parent.width
            toolName: data.tool_name || data.data?.tool_name || ""
            response: data.response || data.data?.response || ""
            isError: data.is_error || data.data?.is_error || false
        }
    }

    // Typing indicator widget (kept for compatibility but no longer rendered separately)
    Component {
        id: typingIndicatorComponent

        TypingIndicator {
            property var widgetColor: root.widgetColor
            active: true
            dotColor: widgetColor
        }
    }

    // Progress widget
    Component {
        id: progressWidgetComponent

        ProgressWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            text: data.progress || data.data?.progress || ""
            percentage: data.percentage || data.data?.percentage || null
        }
    }

    // TodoWrite widget
    Component {
        id: todoWriteWidgetComponent

        TodoWriteWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            todoData: data
        }
    }

    // Image widget
    Component {
        id: imageWidgetComponent

        ImageWidget {
            property var data: ({})
            width: parent.width
            source: data.url || data.data?.url || ""
            caption: data.caption || data.data?.caption || ""
        }
    }

    // Table widget
    Component {
        id: tableWidgetComponent

        TableWidget {
            property var data: ({})
            width: parent.width
            tableData: data.data || {}
        }
    }

    // Link widget
    Component {
        id: linkWidgetComponent

        LinkWidget {
            property var data: ({})
            width: parent.width
            url: data.url || data.data?.url || ""
            title: data.title || data.data?.title || ""
        }
    }

    // Button widget
    Component {
        id: buttonWidgetComponent

        Button {
            property var data: ({})
            text: data.text || data.data?.text || "Button"
            onClicked: {
                if (data.action) {
                    console.log("Button clicked:", data.action)
                }
            }
        }
    }

    // Plan widget
    Component {
        id: planWidgetComponent

        PlanWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            planData: data
        }
    }

    // Task widget
    Component {
        id: taskWidgetComponent

        TaskWidget {
            property var data: ({})
            width: parent.width
            taskData: data
        }
    }

    // File widget
    Component {
        id: fileWidgetComponent

        FileWidget {
            property var data: ({})
            width: parent.width
            filePath: data.path || (data.data && data.data.path) ? data.data.path : ""
            fileName: data.name || (data.data && data.data.name) ? data.data.name : ""
            fileSize: data.size || (data.data && data.data.size) ? data.data.size : 0
        }
    }

    // Video widget
    Component {
        id: videoWidgetComponent

        VideoWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            source: (data.data && data.data.url) ? data.data.url : ""
            caption: data.description || ""
        }
    }

    // Audio widget
    Component {
        id: audioWidgetComponent

        AudioWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            source: (data.data && data.data.url) ? data.data.url : ""
            caption: data.description || ""
        }
    }

    // Chart widget
    Component {
        id: chartWidgetComponent

        ChartWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            chartType: (data.data && data.data.chart_type) ? data.data.chart_type : "bar"
            chartData: (data.data && data.data.data) ? data.data.data : {}
            title: data.title || ""
        }
    }

    // Form widget
    Component {
        id: formWidgetComponent

        FormWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            formData: data.data || {}
        }
    }

    // Step widget
    Component {
        id: stepWidgetComponent

        StepWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            stepData: ({
                title: data.title || "",
                description: data.description || "",
                status: (data.data && data.data.status) ? data.data.status : "pending",
                step_number: (data.data && data.data.step_number) ? data.data.step_number : 0
            })
        }
    }

    // Skill widget
    Component {
        id: skillWidgetComponent

        SkillWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            skillData: (data.data || {})
        }
    }

    // Metadata widget
    Component {
        id: metadataWidgetComponent

        MetadataWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            metadataData: ({
                metadata_type: (data.data && data.data.metadata_type) ? data.data.metadata_type : (data.title || ""),
                title: data.title || "",
                description: data.description || "",
                metadata_data: (data.data && data.data.data) ? data.data.data : ({})
            })
        }
    }

    // Error widget
    Component {
        id: errorWidgetComponent

        ErrorWidget {
            property var data: ({})
            width: parent.width
            errorData: ({
                error_message: (data.data && data.data.error) ? data.data.error : "",
                error_type: (data.data && data.data.error_type) ? data.data.error_type : (data.title || "Error"),
                details: data.description || ""
            })
        }
    }

    // LLM output widget (collapsible)
    Component {
        id: llmOutputComponent

        LlmOutputWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            output: data.output || data.data?.output || ""
            title: data.title || data.data?.title || "LLM Output"
        }
    }
}
