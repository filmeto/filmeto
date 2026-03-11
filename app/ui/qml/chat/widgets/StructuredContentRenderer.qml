// StructuredContentRenderer.qml - Reusable component for rendering structured message content
//
// Content is divided into two sections:
// 1. Content section (top, flat): text, code_block, image, video, audio,
//    link, button, form, file, file_attachment, todo_write
// 2. Thinking section (bottom, collapsible): all other types
//
// PERFORMANCE OPTIMIZATIONS:
// 1. QtObject cache store - avoids property binding chain reactions
// 2. Deep content hash - detects actual content changes
// 3. Lazy thinking section - only loaded when expanded
// 4. Count-based Repeater - avoids array recreation overhead
// 5. Debounced recategorization - batches rapid updates
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

    // ─── Use component properties instead of QtObject for proper binding updates ─────
    // QtObject properties don't trigger binding re-evaluation, causing UI not to update
    // when thinking content is added in real-time
    property string _contentHash: ""
    property int _mainContentCount: 0
    property int _thinkingContentCount: 0
    property int _typingContentCount: 0
    property var _mainItems: []
    property var _thinkingItems: []
    property bool _isStreaming: false
    property bool _initialized: false

    // Main content types lookup
    // Note: plan_task and todo_write are shown in Thinking section (collapsible)
    readonly property var _mainContentTypesLookup: ({
        "text": true, "code_block": true, "image": true, "video": true, "audio": true,
        "link": true, "button": true, "form": true, "file": true, "file_attachment": true,
        "crew_member_read": true, "crew_member_activity": true,
        "llm_output": true, "final": true
    })

    // Deep content hash for change detection
    function _computeContentHash(items) {
        if (!items || items.length === 0) return "empty"
        var hash = items.length.toString()
        var dataLen = 0
        for (var i = 0; i < items.length && i < 5; i++) {
            var item = items[i]
            var type = item.content_type || item.type || "x"
            var title = item.title || item.tool_name || ""
            hash += "|" + type + ":" + title.substring(0, 20)
            if (item.data) {
                var t = item.data.text || item.data.code || item.data.thought || ""
                dataLen += t.length
            }
        }
        hash += "#" + dataLen
        return hash
    }

    // Lazy markdown splitter: expand a single text item into text + code_block segments.
    // Runs in QML only for visible delegates, replacing the Python-side pre-splitting.
    function _splitMarkdownItem(item) {
        var data = item.data || {}
        var text = data.text || ""
        if (!text || (text.indexOf("```") === -1 && text.indexOf("~~~") === -1)) {
            return [item]
        }

        // Check that there are at least two fence markers (open + close or open only)
        var first = text.indexOf("```")
        if (first === -1) first = text.indexOf("~~~")
        var fence = text.substring(first, first + 3)
        var rest = text.substring(first + 3)
        if (rest.indexOf(fence) === -1 && rest.indexOf("~~~") === -1) {
            // Unclosed fence – keep as plain text (streaming partial)
            return [item]
        }

        var baseId = item.content_id || ""
        var status = item.status || "completed"
        var lines = text.split("\n")
        var segments = []
        var textBuf = []
        var codeBuf = []
        var inCode = false
        var fenceMarker = ""
        var codeLang = ""

        for (var li = 0; li < lines.length; li++) {
            var line = lines[li]
            if (!inCode) {
                var m = line.match(/^(`{3,}|~{3,})([\w+#.-]*)\s*$/)
                if (m) {
                    // Flush accumulated text
                    var textStr = textBuf.join("\n").trim()
                    if (textStr) {
                        segments.push({ content_id: baseId + "_s" + segments.length,
                                        content_type: "text",
                                        data: { text: textStr },
                                        status: status })
                    }
                    textBuf = []
                    inCode = true
                    fenceMarker = m[1]
                    codeLang = m[2] || "text"
                    codeBuf = []
                } else {
                    textBuf.push(line)
                }
            } else {
                var stripped = line.trim()
                var isClose = stripped === fenceMarker ||
                    (stripped.length >= fenceMarker.length &&
                     stripped.split("").every(function(c){ return c === fenceMarker[0] }))
                if (isClose) {
                    inCode = false
                    segments.push({ content_id: baseId + "_s" + segments.length,
                                    content_type: "code_block",
                                    data: { code: codeBuf.join("\n"), language: codeLang },
                                    status: status })
                    codeBuf = []
                } else {
                    codeBuf.push(line)
                }
            }
        }

        // Unclosed fence: treat remaining as plain text
        if (inCode) {
            textBuf.push(fenceMarker + codeLang)
            for (var ci = 0; ci < codeBuf.length; ci++) textBuf.push(codeBuf[ci])
        }

        var tailText = textBuf.join("\n").trim()
        if (tailText) {
            segments.push({ content_id: baseId + "_s" + segments.length,
                            content_type: "text",
                            data: { text: tailText },
                            status: status })
        }

        return segments.length > 0 ? segments : [item]
    }

    // Single-pass content categorization (with lazy markdown splitting for text items)
    function _categorizeContent() {
        var src = root.structuredContent

        // Empty content fallback
        if (!src || src.length === 0) {
            root._mainItems = root.content ? [{ content_type: "text", text: root.content }] : []
            root._thinkingItems = []
            root._isStreaming = false
            root._mainContentCount = root._mainItems.length
            root._thinkingContentCount = 0
            root._typingContentCount = 0
            root._initialized = true
            return
        }

        // Basic support mode - pass through without splitting
        if (root.widgetSupport !== "full") {
            root._mainItems = src
            root._thinkingItems = []
            root._isStreaming = false
            root._mainContentCount = src.length
            root._thinkingContentCount = 0
            root._typingContentCount = 0
            root._initialized = true
            return
        }

        // Single pass: categorize + lazily split text items containing code fences
        var mainItems = []
        var thinkingItems = []
        var hasTypingStart = false
        var hasCrewMemberActivity = false
        var mainTypes = root._mainContentTypesLookup

        for (var i = 0; i < src.length; i++) {
            var item = src[i]
            var type = item.content_type || item.type || "text"

            if (type === "typing") {
                // Add typing content to main items for display
                mainTypes[type] = true
                mainItems.push(item)
                var data = item.data || {}
                if ((data.state || "start") === "start") {
                    hasTypingStart = true
                }
            } else if (type === "crew_member_activity") {
                hasCrewMemberActivity = true
                mainItems.push(item)
            } else if (type === "text") {
                // Lazily split text items with code fences into text/code_block segments
                var segs = _splitMarkdownItem(item)
                for (var s = 0; s < segs.length; s++) {
                    mainItems.push(segs[s])
                }
            } else if (mainTypes[type] === true) {
                mainItems.push(item)
            } else {
                thinkingItems.push(item)
            }
        }

        root._mainItems = mainItems
        root._thinkingItems = thinkingItems
        root._isStreaming = hasTypingStart || hasCrewMemberActivity
        root._mainContentCount = mainItems.length
        root._thinkingContentCount = thinkingItems.length
        root._typingContentCount = hasTypingStart ? 1 : 0
        root._initialized = true
    }

    // Debounced content update timer
    Timer {
        id: contentUpdateTimer
        interval: 32  // ~30fps debounce
        repeat: false
        onTriggered: {
            var newHash = root._computeContentHash(root.structuredContent)
            if (newHash !== root._contentHash) {
                root._contentHash = newHash
                root._categorizeContent()
            }
        }
    }

    onStructuredContentChanged: contentUpdateTimer.restart()
    onContentChanged: contentUpdateTimer.restart()

    // Initial categorization
    Component.onCompleted: {
        root._categorizeContent()
    }

    // Exposed readonly properties
    readonly property var mainContentItems: root._mainItems
    readonly property var thinkingItems: root._thinkingItems
    readonly property bool isStreaming: root._isStreaming
    readonly property bool hasThinkingSection: (root._thinkingContentCount > 0 || root._isStreaming) && widgetSupport === "full"
    readonly property bool isInitialized: root._initialized

    // Thinking section state
    property bool thinkingExpanded: false
    property bool thinkingContentLoaded: false

    // Lazy thinking summary - only computed when section is visible AND expanded
    function _getThinkingSummary() {
        if (!root.hasThinkingSection || !root.thinkingContentLoaded) return ""

        var items = root._thinkingItems
        if (items.length > 0) {
            var latest = items[items.length - 1]
            return _computeSummary(latest)
        }

        if (root._isStreaming && root._mainContentCount > 0) {
            var latestMain = root._mainItems[root._mainItems.length - 1]
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
        return ""
    }

    function _computeSummary(item) {
        if (!item) return ""
        var type = item.content_type || item.type || ""
        var data = item.data || {}

        switch (type) {
            case "thinking":
                var thought = data.thought || item.thought || ""
                return thought ? thought.replace(/\n/g, " ").substring(0, 100) : ""
            case "tool_call":
                var tn = data.tool_name || item.tool_name || ""
                var st = data.status || item.status || ""
                if (tn) {
                    if (st === "started" || st === "running") return "🔧 " + tn + "..."
                    if (st === "completed" || st === "success") return "🔧 " + tn + " ✓"
                    if (st === "error" || st === "failed") return "🔧 " + tn + " ✗"
                    return "🔧 " + tn
                }
                return ""
            case "tool_response":
                return "📋 " + (data.tool_name || item.tool_name || "Response")
            case "skill":
                return "⚡ " + (data.name || item.title || "Skill")
            case "step":
                return item.title || data.title || ""
            case "plan":
                return "📋 " + (item.title || "Plan")
            case "progress":
                return (data.progress || item.progress || "").substring(0, 50)
            case "llm_output":
                return "💬 " + (item.title || data.title || "LLM Output")
            case "error":
                return "❌ " + (data.error || item.title || "Error")
            case "metadata":
                return item.title || data.metadata_type || ""
            default:
                return item.title || item.description || type
        }
    }

    function _resolveComponent(type) {
        switch (type) {
            case "text": return textWidgetComponent
            case "code_block": return codeBlockComponent
            case "thinking": return widgetSupport === "full" ? thinkingWidgetComponent : textWidgetComponent
            case "tool_call": return widgetSupport === "full" ? toolCallComponent : textWidgetComponent
            case "tool_response": return widgetSupport === "full" ? toolResponseComponent : textWidgetComponent
            case "image": return imageWidgetComponent
            case "video": return widgetSupport === "full" ? videoWidgetComponent : textWidgetComponent
            case "audio": return widgetSupport === "full" ? audioWidgetComponent : textWidgetComponent
            case "table": return widgetSupport === "full" ? tableWidgetComponent : textWidgetComponent
            case "chart": return widgetSupport === "full" ? chartWidgetComponent : textWidgetComponent
            case "link": return linkWidgetComponent
            case "button": return widgetSupport === "full" ? buttonWidgetComponent : textWidgetComponent
            case "form": return widgetSupport === "full" ? formWidgetComponent : textWidgetComponent
            case "file_attachment":
            case "file": return fileWidgetComponent
            case "plan": return widgetSupport === "full" ? planWidgetComponent : textWidgetComponent
            case "plan_task": return widgetSupport === "full" ? planTaskWidgetComponent : textWidgetComponent
            case "task_list":
            case "task": return widgetSupport === "full" ? taskWidgetComponent : textWidgetComponent
            case "step": return widgetSupport === "full" ? stepWidgetComponent : textWidgetComponent
            case "skill": return widgetSupport === "full" ? skillWidgetComponent : textWidgetComponent
            case "progress": return widgetSupport === "full" ? progressWidgetComponent : textWidgetComponent
            case "todo_write": return widgetSupport === "full" ? todoWriteWidgetComponent : textWidgetComponent
            case "metadata": return widgetSupport === "full" ? metadataWidgetComponent : textWidgetComponent
            case "error": return widgetSupport === "full" ? errorWidgetComponent : textWidgetComponent
            case "llm_output": return widgetSupport === "full" ? llmOutputComponent : textWidgetComponent
            case "typing": return widgetSupport === "full" ? typingComponent : textWidgetComponent
            case "final": return textWidgetComponent
            case "crew_member_read": return widgetSupport === "full" ? crewMemberReadComponent : textWidgetComponent
            case "crew_member_activity": return widgetSupport === "full" ? crewMemberActivityComponent : textWidgetComponent
            default: return textWidgetComponent
        }
    }

    Column {
        id: contentColumn
        spacing: 8
        width: parent.width

        // ─── Content Section (flat display, always visible) ─────────
        Repeater {
            model: root._mainContentCount

            delegate: Loader {
                id: mainWidgetLoader
                width: contentColumn.width

                property var widgetData: root._mainItems[index] || ({})
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
                    if (loadedItem && loadedItem.hasOwnProperty('data')) {
                        loadedItem.data = widgetData
                    }
                    if (loadedItem && loadedItem.hasOwnProperty('widgetColor')) {
                        loadedItem.widgetColor = root.widgetColor
                    }
                }

                height: loadedItem ? (loadedItem.implicitHeight || loadedItem.height || 0) : 0
            }
        }

        // ─── Thinking Section (collapsible, LAZY LOADED) ──────────
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
                                    return root._thinkingContentCount > 0
                                        ? "Thinking (" + root._thinkingContentCount + ")"
                                        : "Thinking..."
                                }
                                var count = root._thinkingContentCount
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
                            text: root._getThinkingSummary()
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.38)
                            font.pixelSize: 11
                            elide: Text.ElideRight
                            maximumLineCount: 1
                        }

                        // Expand/collapse arrow (only when there are items)
                        Text {
                            visible: root._thinkingContentCount > 0
                            text: root.thinkingExpanded ? "▲" : "▼"
                            color: Qt.rgba(root.textColor.r, root.textColor.g, root.textColor.b, 0.4)
                            font.pixelSize: 9
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: root._thinkingContentCount > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (root._thinkingContentCount > 0) {
                                root.thinkingExpanded = !root.thinkingExpanded
                            }
                        }
                    }
                }

                // Expanded thinking content area - LAZY LOADED
                Loader {
                    id: thinkingContentLoader
                    visible: root.thinkingExpanded && root._thinkingContentCount > 0
                    width: parent.width
                    height: visible ? (item ? item.implicitHeight : 0) : 0

                    // Key optimization: only activate when expanded
                    active: root.thinkingExpanded && root._thinkingContentCount > 0

                    onActiveChanged: {
                        if (active) {
                            root.thinkingContentLoaded = true
                        }
                    }

                    sourceComponent: Rectangle {
                        implicitHeight: thinkingContentCol.height + 16
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
                                model: root._thinkingContentCount

                                delegate: Loader {
                                    id: thinkingWidgetLoader
                                    width: thinkingContentCol.width

                                    property var widgetData: root._thinkingItems[index] || ({})
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
                                        if (loadedItem && loadedItem.hasOwnProperty('data')) {
                                            loadedItem.data = widgetData
                                        }
                                        if (loadedItem && loadedItem.hasOwnProperty('widgetColor')) {
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
    }

    // ─────────────────────────────────────────────────────────────
    // Widget Components
    // ─────────────────────────────────────────────────────────────

    // Text widget with markdown rendering, selection and copy support
    Component {
        id: textWidgetComponent

        MarkdownText {
            property var data: ({})
            text: data.text || data.data?.text || ""
            textColor: root.textColor
            fontPixelSize: 14
            wrapMode: true
            selectionColor: root.widgetColor
            width: parent.width
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
            toolName: data.data?.tool_name || data.tool_name || ""
            toolArgs: data.data?.tool_input || data.tool_input || data.data?.tool_args || data.tool_args || {}
            toolStatus: data.data?.status || data.status || "started"
            result: data.data?.result !== undefined ? data.data.result : (data.result !== undefined ? data.result : null)
            error: data.data?.error || data.error || ""
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
            planData: data.data || data
            mode: "inline"
        }
    }

    // PlanTask widget (single task status update)
    Component {
        id: planTaskWidgetComponent

        PlanTaskWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
            updateData: data.data || data
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

    // Typing indicator widget
    Component {
        id: typingComponent

        Item {
            property var data: ({})

            width: parent ? parent.width : 0
            height: 20

            Text {
                anchors.centerIn: parent
                // Check both data.state and data.data.state for compatibility
                text: (data.state || (data.data && data.data.state) || "start") === "end" ? "✓" : "typing..."
                color: root.textColor
                font.pixelSize: 12
            }
        }
    }

    // CrewMemberRead widget
    Component {
        id: crewMemberReadComponent

        CrewMemberReadWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
        }
    }

    // CrewMemberActivity widget (thinking/typing indicator)
    Component {
        id: crewMemberActivityComponent

        CrewMemberActivityWidget {
            property var data: ({})
            width: parent.width
            widgetColor: root.widgetColor
        }
    }
}
