---
name: read_single_scene
description: 读取和检索单个剧本场景的技能
---

# 单个场景读取技能

此技能允许代理从项目的剧本中读取和检索单个场景。它提供场景内容和元数据的访问权限，用于分析、审查或作为进一步创作工作的上下文。

## 功能

- 通过唯一的 scene_id 读取单个场景
- 检索好莱坞剧本格式的场景内容
- 访问场景元数据，包括地点、时间、角色、故事节拍等
- 根据需要过滤响应以仅包含内容或仅包含元数据
- 提供结构化的场景信息以进行分析或修订

## 约束

- **需要上下文**：此技能需要有效的 ToolContext 和剧本管理器的访问权限
- **需要剧本管理器**：项目必须具有初始化的剧本管理器并存储了场景
- **有效的 scene_id**：scene_id 必须存在于剧本中；否则返回错误
- **只读**：此技能仅读取场景，不修改它们

## 输入要求

通过 `execute_skill_script` 调用脚本时提供以下输入：

- `scene_id`（字符串，必需）：场景标识符（例如 `scene_001`）。
- `include_content`（布尔值，可选，默认：true）：包含完整的场景内容。
- `include_metadata`（布尔值，可选，默认：true）：包含场景元数据。

如果缺少 `scene_id`，请在最终响应中询问，而不是调用脚本。

## 使用方法

当代理需要审查现有场景、分析场景结构或使用场景内容作为编写或修订其他场景的上下文时，可以调用此技能。

**最佳实践：**
- 当编剧或导演需要审查特定场景时使用
- 用于在进行修订前分析场景结构、对话或动作
- 可用于引用之前的场景以编写续集或相关场景
- 当只需要元数据时设置 include_content=false（响应更快）
- 当只需要场景文本时设置 include_metadata=false

## 参数示例

```json
{
  "scene_id": "scene_001",
  "include_content": true,
  "include_metadata": true
}
```

## 输出

返回包含以下内容的 JSON 对象：
- `success`：指示操作是否成功的布尔值
- `scene_id`：已读取的场景的 ID
- `title`：场景的标题
- `content`：场景内容（如果 include_content=true）
- `metadata`：包含场景元数据的对象（如果 include_metadata=true）：
  - `scene_number`：剧本中的场景编号
  - `location`：场景的地点
  - `time_of_day`：场景的时间
  - `genre`：类型分类
  - `logline`：场景的简要总结
  - `characters`：场景中的角色列表
  - `story_beat`：故事节拍或情节点
  - `page_count`：预估页数
  - `duration_minutes`：预估时长
  - `tags`：分类标签
  - `status`：工作流状态（draft、revised、final、approved）
  - `revision_number`：当前修订号
  - `created_at`：创建时间戳
  - `updated_at`：最后更新时间戳
- `message`：人类可读的状态消息

## 错误处理

- 如果缺少 scene_id 参数，则返回错误
- 如果指定的 scene_id 在剧本中不存在，则返回错误
- 如果上下文中没有剧本管理器，则返回错误
- 检查响应中的 `success` 字段以验证操作是否成功完成
