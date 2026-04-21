# AgentMessageBubble 调试指南

## 如何查看调试输出

### 1. 运行应用并查看控制台

当您运行应用时，控制台会显示类似以下的调试输出：

```
[DEBUG] _load_recent_conversation() called
[DEBUG] Project found: <project object>
[DEBUG] History instance: <MessageLogHistory object>
[DEBUG] raw_messages count: 5
[DEBUG] Loading 5 messages into model...
[DEBUG]   Processing message 1/5...
[DEBUG] _load_message_from_history() - keys: ['message_id', 'sender_id', 'sender_name', 'timestamp', 'structured_content']
[DEBUG]   structured_content: [{'content_id': '...', 'content_type': 'text', 'data': {...}}, ...]
[DEBUG] Parsing message: a1b2c3d4... from 王小林
[DEBUG] content_list length: 1
[DEBUG]   Parsed content[0]: TextContent - content_type=ContentType.TEXT
[DEBUG]     text: 我正在以制片人的身份...
[DEBUG]   Agent message with 1 content items
[DEBUG]   QML structuredContent length: 1
[DEBUG]   First item content_type: text
[DEBUG] Model now has 5 items
```

### 2. 检查关键输出

请检查以下关键输出项：

#### A. 历史数据加载
```
[DEBUG] raw_messages count: X
```
- 如果是 `0`：历史存储为空，需要先发送消息
- 如果有数字：继续检查下一步

#### B. 消息解析
```
[DEBUG] Parsing message: xxx... from <sender_name>
[DEBUG] content_list length: X
```
- 如果 `content_list length: 0`：数据格式可能有问题
- 如果有数字：继续检查

#### C. 内容解析
```
[DEBUG]   Parsed content[0]: <ContentType> - content_type=<ContentType>
[DEBUG]     text: ...
```
- 如果看到解析错误：数据格式问题
- 如果解析成功但 `structured_content` 为空：检查下面

#### D. QML 数据转换
```
[DEBUG]   QML structuredContent length: X
[DEBUG]   First item content_type: <type>
```
- 如果长度为 `0`：转换过程有问题
- 如果有数据：继续检查

#### E. 模型状态
```
[DEBUG] Model now has X items
```
- 如果是 `0`：数据没有添加到模型
- 如果有数字：数据已添加到模型

### 3. 常见问题诊断

#### 问题 1: 历史数据为空
```
[DEBUG] raw_messages count: 0
[WARNING] No messages found in history
```
**解决方案**: 先发送一条消息来创建历史数据

#### 问题 2: content_list 为空
```
[DEBUG] content_list length: 0
```
**可能原因**:
- 历史数据使用了旧格式 (`content` 字段)
- 数据格式不正确

**检查**: 查看 `structured_content` 字段的内容

#### 问题 3: structured_content 解析失败
```
[WARNING] Failed to load structured content[0]: <error>
[WARNING] content_item: {...}
```
**解决方案**: 检查数据格式是否正确

#### 问题 4: 模型中没有数据
```
[DEBUG] Model now has 0 items
```
**可能原因**:
- 消息被跳过（系统消息等）
- 数据转换为 ChatListItem 失败

**检查**: 查看是否有 "Skipping system event" 或 "Failed to build item" 的输出

### 4. 如果仍然看不到内容

如果您看到调试输出显示数据正确加载，但 QML 界面仍然没有显示内容，可能是 QML 渲染问题。

#### 检查 QML 组件加载
在 QML 中添加 console.log 来调试：

```qml
// AgentChatList.qml
Component {
    id: agentComponent

    AgentMessageBubble {
        Component.onCompleted: {
            console.log("[QML] AgentMessageBubble loaded")
            console.log("[QML] senderName:", senderName)
            console.log("[QML] structuredContent length:", structuredContent.length)
            console.log("[QML] structuredContent:", JSON.stringify(structuredContent))
        }
    }
}
```

### 5. 运行独立测试

```bash
# 测试历史数据
python tests/test_app/test_ui/test_real_history_data.py

# 测试数据解析流程
python tests/test_app/test_ui/test_history_to_qml.py

# 测试 QML 组件
python tests/test_app/test_ui/test_content_debug.py
```

## 修改摘要

### 已修复的文件

1. **app/ui/chat/qml/components/AgentMessageBubble.qml**
   - Loader 宽度改用 anchors (line 169-170)

2. **app/ui/chat/qml/components/UserMessageBubble.qml**
   - Loader 宽度改用 anchors (line 119-120)

3. **app/ui/chat/qml/AgentChatList.qml**
   - 字段名修正: `userName: modelData.senderName` (line 95)
   - 字段名修正: `userIcon: modelData.agentIcon` (line 96)

4. **app/ui/chat/list/qml_agent_chat_list_widget.py**
   - 支持旧格式 `content` 字段 (line 385-388)
   - 添加详细调试输出 (line 400-430, 468-486, 509-529)

### 下一步

1. 运行应用并查看控制台输出
2. 根据输出诊断问题
3. 如果需要，添加 QML 调试输出
