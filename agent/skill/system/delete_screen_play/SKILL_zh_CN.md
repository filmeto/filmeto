---
name: delete_screen_play
description: |-
  用途：从项目中删除多个或全部剧本场景，用于重大重构或重新开始。
  能力：一次性删除所有场景或按ID选择性删除特定场景、验证删除状态。
  触发：当用户说"删除剧本"、"清空剧本"、"删除场景"、"删除所有场景"或想要重新开始时。
---

# 剧本删除技能

从项目中删除剧本场景。两种模式：删除全部场景，或按 scene_ids 删除指定场景。

## 执行优先级（重要）

**收到删除意图后立即执行，不要：**
- 先通读剧本或列出全部场景再删（除非部分删除需要 scene_ids）
- 再次向用户确认——"删除剧本"/"清空剧本"等即表示明确意图，直接执行
- 在执行前花多步做警告或备份建议

**应当：**
- 用户说删除/清空剧本（全部）时：在同一或下一步即调用 `execute_skill_script`，技能 `delete_screen_play`，参数 `{"delete_mode": "all"}`
- 用户要删指定场景时：先取得 scene_ids（如从列表或用户消息），再以 `delete_mode: "partial"` 和 `scene_ids` 调用
- 执行后根据脚本返回汇报 deleted_count、message

## 功能

- 删除项目中全部剧本场景（完全清理）
- 按 scene_ids 删除指定场景（选择性清理）
- 处理场景不存在的情况

## 约束

- **需要上下文**：有效的 ToolContext 与剧本管理器
- **不可逆**：会永久删除场景文件

## 输入要求

通过 `execute_skill_script` 调用时：

### 完全删除
- `delete_mode`（字符串）：`"all"`
- 无需其他参数

### 部分删除
- `delete_mode`（字符串）：`"partial"`
- `scene_ids`（字符串列表，必需）：如 `["scene_001", "scene_002"]`

当用户已表达"删除全部"/"清空剧本"且参数明确时，不要再次确认，直接调用脚本。仅在模式或 scene_ids 确实不明确时才询问。

## 示例参数

### 删除所有场景：
```json
{
  "delete_mode": "all"
}
```

### 删除特定场景：
```json
{
  "delete_mode": "partial",
  "scene_ids": ["scene_001", "scene_002", "scene_003"]
}
```

## 输出

返回一个JSON对象，包含：
- `success`：布尔值，指示操作是否成功
- `delete_mode`：使用的模式（"all" 或 "partial"）
- `deleted_count`：实际删除的场景数量
- `deleted_scene_ids`：已删除的场景ID列表
- `message`：人类可读的状态消息

成功响应示例（完全删除）：
```json
{
  "success": true,
  "delete_mode": "all",
  "deleted_count": 10,
  "deleted_scene_ids": ["scene_001", "scene_002", "..."],
  "message": "成功删除了所有10个剧本场景。"
}
```

成功响应示例（部分删除）：
```json
{
  "success": true,
  "delete_mode": "partial",
  "deleted_count": 3,
  "deleted_scene_ids": ["scene_001", "scene_002", "scene_003"],
  "message": "成功删除了3个剧本场景。"
}
```

场景不存在时的示例：
```json
{
  "success": true,
  "delete_mode": "all",
  "deleted_count": 0,
  "deleted_scene_ids": [],
  "message": "未找到剧本场景。无需删除。"
}
```

## 错误处理

- 如果缺少 `delete_mode` 或其无效，则返回错误
- 如果部分模式下缺少 `scene_ids`，则返回错误
- 如果上下文中没有可用的剧本管理器，则返回错误
- 如果没有可删除的场景，则返回成功并设置 deleted_count=0
