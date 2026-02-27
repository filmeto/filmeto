---
name: delete_screen_play
description: 用于删除项目中剧本场景的技能 - 支持完全删除或部分场景删除
---

# 剧本删除技能

此技能允许代理从项目中删除剧本场景。它支持两种模式：完全删除所有场景，或选择性删除特定场景。

## 功能

- 删除项目中的所有剧本场景（完全清理）
- 根据场景ID删除特定场景（选择性清理）
- 验证删除状态
- 处理场景不存在的情况

## 约束

- **需要上下文**：此技能需要有效的ToolContext，并具有对剧本管理器的访问权限
- **需要剧本管理器**：项目必须已初始化剧本管理器
- **危险操作**：此技能会永久删除场景文件 - 请极其谨慎地使用

## 输入要求

通过 `execute_skill_script` 调用脚本时，请提供以下输入：

### 完全删除（删除所有场景）
- `delete_mode`（字符串）：必须为 `"all"` 以删除所有场景
- 不需要其他参数

### 部分删除（删除特定场景）
- `delete_mode`（字符串）：必须为 `"partial"` 以删除特定场景
- `scene_ids`（字符串列表，必需）：要删除的场景标识符列表（例如 `["scene_001", "scene_002"]`）

如果缺少必需参数，请在最终响应中询问，而不是调用脚本。

## 何时使用此技能

**这是一个危险操作。仅在以下情况下使用此技能：**

1. 当前剧本完全无法满足需求，需要从头重写
2. 存在无法通过编辑修复的根本性故事结构问题
3. 用户明确要求清空剧本
4. 重大情节修改需要删除多个场景

**不要在以下情况下使用此技能：**
- 小幅场景调整（请改用 `update` 操作）
- 删除单个场景（请改用 `delete_single_scene` 技能）
- 简单的对话或描述更改（请改用 `update` 操作）

## 重要警告

**在执行此技能之前：**
1. 始终与用户确认他们想要继续删除
2. 明确说明将删除哪些场景（全部或特定列表）
3. 警告此操作无法撤销
4. 考虑建议先备份剧本

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
