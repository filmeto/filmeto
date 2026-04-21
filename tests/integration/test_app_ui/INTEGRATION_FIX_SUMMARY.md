# AgentMessageBubble Content Display Fix - Integration

## Problem Summary

测试页面中内容正常显示，但集成到 agent_chat_widget 中从 agent_chat_history 加载数据时内容不显示。

## Root Causes Found

### 1. Loader Width Issue (AgentMessageBubble.qml)
**File**: `app/ui/chat/qml/components/AgentMessageBubble.qml:166-170`

**Problem**: Loader 的宽度绑定在初始化时为 0
```qml
// Before (broken)
delegate: Loader {
    width: Math.max(0, contentColumn.width)  // contentColumn.width = 0 at init!
```

**Solution**: 使用 anchors 填充父容器宽度
```qml
// After (fixed)
delegate: Loader {
    anchors.left: parent.left
    anchors.right: parent.right
```

### 2. Loader Width Issue (UserMessageBubble.qml)
**File**: `app/ui/chat/qml/components/UserMessageBubble.qml:117-120`

**Problem**: Loader 使用计算宽度，可能在初始化时为 0
```qml
// Before (broken)
delegate: Loader {
    width: availableWidth  // May be 0 at init
```

**Solution**: 使用 anchors
```qml
// After (fixed)
delegate: Loader {
    anchors.left: parent.left
    anchors.right: parent.right
```

### 3. Field Name Mismatch (AgentChatList.qml)
**File**: `app/ui/chat/qml/AgentChatList.qml:95-96`

**Problem**: QML 使用 `userName` 和 `userIcon`，但 Python 模型提供的是 `senderName` 和 `agentIcon`
```qml
// Before (broken)
userName: modelData.userName || "You"
userIcon: modelData.userIcon || "👤"
```

**Solution**: 使用正确的字段名
```qml
// After (fixed)
userName: modelData.senderName || "You"
userIcon: modelData.agentIcon || "👤"
```

### 4. Old Format Support (qml_agent_chat_list_widget.py)
**File**: `app/ui/chat/list/qml_agent_chat_list_widget.py:383-388`

**Problem**: 只支持新格式 `structured_content`，不支持旧格式 `content`
```python
# Before (broken)
content_list = msg_data.get("structured_content", [])
```

**Solution**: 同时支持新旧格式
```python
# After (fixed)
content_list = msg_data.get("structured_content") or msg_data.get("content", [])
if not content_list:
    # Also check metadata for legacy data
    content_list = metadata.get("structured_content") or metadata.get("content", [])
```

## Files Changed

1. `app/ui/chat/qml/components/AgentMessageBubble.qml` - Loader width fix
2. `app/ui/chat/qml/components/UserMessageBubble.qml` - Loader width fix
3. `app/ui/chat/qml/AgentChatList.qml` - Field name fix
4. `app/ui/chat/list/qml_agent_chat_list_widget.py` - Old format support + debug logging

## Test Files Created

1. `tests/test_app/test_ui/test_content_bubble.qml` - Full QML test interface
2. `tests/test_app/test_ui/test_content_bubble_debug.qml` - Simplified debug test
3. `tests/test_app/test_ui/test_content_display.py` - Python test runner
4. `tests/test_app/test_ui/test_content_debug.py` - Debug test runner
5. `tests/test_app/test_ui/test_history_loading.py` - Data format test
6. `tests/test_app/test_ui/test_history_to_qml.py` - Complete flow test
7. `tests/test_app/test_ui/test_build_item_simulation.py` - Build item simulation test

## Running Tests

```bash
# QML widget test (standalone)
python tests/test_app/test_ui/test_content_debug.py

# Full content display test
python tests/test_app/test_ui/test_content_display.py

# History loading test
python tests/test_app/test_ui/test_history_to_qml.py

# Build item simulation test
python tests/test_app/test_ui/test_build_item_simulation.py
```

## Verification

在 agent_chat_widget 中加载历史数据时，检查以下内容：
- [ ] 文本消息正确显示
- [ ] 长文本正确换行
- [ ] 错误消息正确显示
- [ ] Thinking 内容正确显示
- [ ] Code block 正确渲染
- [ ] Tool call/response 正确显示
- [ ] Progress 正确显示
- [ ] Typing indicator 正确隐藏
- [ ] 多个 content 类型按顺序显示
- [ ] 用户消息正确显示（使用 senderName）
