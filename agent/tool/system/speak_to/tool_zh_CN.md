# speak_to

在不同可见性模式下发送剧组成员之间的消息。

## 描述

此工具使剧组成员能够通过 FilmetoAgent 的消息路由系统进行通信。它支持三种具有不同可见性和路由行为的通信模式。

## 参数

| 名称 | 类型 | 必填 | 描述 |
|------|------|----------|-------------|
| mode | string | 是 | 通信模式："public"、"specify" 或 "private" |
| message | string | 是 | 要发送的消息内容 |
| target | string | 条件必填 | 目标剧组成员名称（"specify" 和 "private" 模式必填） |

## 模式说明

### public（公开模式）
- 消息发送给 FilmetoAgent，通过常规路由逻辑处理
- 对话历史中所有剧组成员可见
- 可能由制片人或任何相关剧组成员处理

### specify（指定模式）
- 消息以 @提及 格式开头（例如："@导演 请审阅这个"）
- 对话历史中所有剧组成员可见
- 通常路由到并被提及的剧组成员处理

### private（私密模式）
- 消息直接发送给目标剧组成员
- 不会记录在对话历史中
- 不通过 FilmetoAgent 的路由逻辑处理
- 用于剧组成员之间的直接、私密通信

## 示例

### 公开消息
```json
{
    "mode": "public",
    "message": "我已完成场景分析，准备接受审阅。"
}
```

### 指定消息
```json
{
    "mode": "specify",
    "target": "director",
    "message": "请审阅我刚创建的故事板。"
}
```

### 私密消息
```json
{
    "mode": "private",
    "target": "cinematographer",
    "message": "你能帮我设置第5场戏的灯光吗？"
}
```

## 返回值

| 字段 | 类型 | 描述 |
|-------|------|-------------|
| mode | string | 使用的通信模式 |
| success | boolean | 消息是否发送成功 |
| target | string | 目标剧组成员（specify/private 模式） |
| message | string | 成功消息 |
| message_id | string | 消息的唯一标识符 |

## 注意事项

- 发送者不应向自己发送消息（尤其是制片人）
- 私密消息绕过历史记录以确保保密性
- 指定模式使用 @提及 格式，在保持可见性的同时实现明确的目标指向
