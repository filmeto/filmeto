---
name: delete_single_scene
description: |-
  用途：从剧本中删除不再需要的单个场景。
  能力：通过scene_id删除场景、验证删除状态、优雅处理不存在的场景。
  触发：明确的用户指令，如"删除场景"、"删除scene_001"、"移除第3个场景"、"删除场景"等。
---

# 单个场景删除技能

此技能允许代理根据明确的用户指令从项目的剧本中删除单个场景。

## 意图识别

当用户明确请求删除场景时应调用此技能：

**触发模式（英文）：**
- "delete scene [scene_id/scene number]"
- "remove scene [scene_id/scene number]"
- "delete scene number X"
- "remove scene X from the screenplay"
- "delete the [first/second/third...] scene"

**触发模式（中文）：**
- "删除场景 [场景ID/场景编号]"
- "移除场景 [场景ID/场景编号]"
- "删除第X个场景"
- "把场景X删掉"

## 功能

- 通过唯一的 scene_id 删除单个场景
- 从自然语言中解析场景标识符（例如 "scene_001"、"scene 1"、"第一个场景"）
- 从剧本目录中删除场景文件
- 验证删除状态
- 处理场景不存在的情况

## 执行流程

处理场景删除请求时，请按照以下步骤执行：

### 步骤 1：从用户输入中提取 scene_id
解析用户的命令以识别场景标识符：
- 如果用户提供了明确的 scene_id（例如 "scene_001"、"scene_3"）：直接使用
- 如果用户按编号引用场景（例如 "scene 1"、"第1个场景"）：转换为 scene_id 格式（scene_001）
- 如果用户说"第一个场景"、"第二个场景"：从剧本中映射序数到实际的 scene_id
- **如果无法确定 scene_id**：请用户指定要删除的场景

### 步骤 2：确认用户（可选但建议）
执行删除前，请与用户确认：
- "您确定要删除场景 [scene_id] 吗？此操作无法撤销。"
- 如果用户确认，继续步骤 3

### 步骤 3：执行删除
使用提取的 `scene_id` 参数调用技能脚本：
```python
execute_skill_script("delete_single_scene", {"scene_id": "scene_001"})
```

### 步骤 4：报告结果
解析响应并通知用户：
- 如果 success=true 且 deleted=true： "场景 'scene_001' 已成功删除。"
- 如果 success=true 且 deleted=false： "场景 'scene_999' 不存在。无需删除。"
- 如果 success=false： 向用户报告错误消息

## 约束

- **需要剧本管理器**：项目必须具有初始化的剧本管理器
- **有效的 scene_id**：scene_id 应该存在；删除不存在的场景返回成功（幂等操作）
- **破坏性操作**：此技能永久删除场景文件 - 请谨慎使用

## 输入要求

通过 `execute_skill_script` 调用脚本时提供以下输入：

- `scene_id`（字符串，必需）：场景标识符（例如 `scene_001`）。

如果缺少 `scene_id`，请在最终响应中询问，而不是调用脚本。

**重要提示**：删除之前，请考虑：
- 与用户确认是否应继续此操作
- 检查其他场景是否引用此场景
- 考虑是否应归档场景而不是删除

## 使用方法

当代理需要删除以下场景时，可以调用此技能：
- 故事中不再需要的场景
- 其他场景的重复场景
- 被修订版本替换的场景
- 故事重构的一部分

**最佳实践：**
- 删除前始终验证 scene_id
- 考虑先读取场景以确认它是正确的场景
- 警告用户关于永久删除的操作
- 谨慎使用，因为此操作无法撤销

## 参数示例

```json
{
  "scene_id": "scene_001"
}
```

## 输出

返回包含以下内容的 JSON 对象：
- `success`：指示操作是否成功的布尔值
- `scene_id`：已删除的场景的 ID
- `deleted`：指示场景是否实际被删除的布尔值（如果场景不存在则为 false）
- `message`：人类可读的状态消息

成功响应示例：
```json
{
  "success": true,
  "scene_id": "scene_001",
  "deleted": true,
  "message": "场景 'scene_001' 已成功删除。"
}
```

场景不存在时的示例：
```json
{
  "success": true,
  "scene_id": "scene_999",
  "deleted": false,
  "message": "场景 'scene_999' 不存在。无需删除。"
}
```

## 错误处理

- 如果缺少 scene_id 参数，则返回错误
- 如果上下文中没有剧本管理器，则返回错误
- 如果场景不存在，返回成功但 deleted=false（幂等操作）
- 检查响应中的 `success` 字段以验证操作是否成功完成
