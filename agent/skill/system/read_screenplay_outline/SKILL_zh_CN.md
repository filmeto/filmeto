---
name: read_screenplay_outline
description: 读取包含所有场景摘要的剧本大纲的技能
---

# 剧本大纲读取技能

此技能允许代理读取完整的剧本大纲，这是项目中所有场景的结构化摘要。它提供故事结构的全面视图，按时间顺序显示场景摘要和关键元数据。

## 功能

- 读取包含所有场景摘要的完整剧本大纲
- 检索场景元数据，包括标题、摘要、地点、角色和故事节拍
- 按场景编号、创建日期、更新日期或标题对场景进行排序
- 按状态过滤场景（草稿、修订、最终、批准）
- 可选择包含完整的场景内容以进行详细审查
- 提供整个故事结构的结构化概述

## 约束

- **需要上下文**：此技能需要有效的 ToolContext 和剧本管理器的访问权限
- **需要剧本管理器**：项目必须具有初始化的剧本管理器并存储了场景
- **只读**：此技能仅读取场景，不修改它们
- **空大纲**：如果不存在场景，则返回空的大纲列表

## 输入要求

通过 `execute_skill_script` 调用脚本时提供以下输入：

- `include_content`（布尔值，可选，默认：false）：包含完整的场景内容（为 false 时仅包含元数据）。
- `sort_by`（字符串，可选，默认："scene_number"）：按"scene_number"、"created_at"、"updated_at"或"title"排序。
- `filter_status`（字符串，可选）：按状态"draft"、"revised"、"final"或"approved"过滤。

## 使用方法

当编剧或导演需要以下操作时，可以调用此技能：
- 审查整体故事结构
- 了解场景流程和节奏
- 规划修订或新场景
- 识别叙事中的空白
- 在编写特定场景之前获取上下文

**最佳实践：**
- 使用 include_content=false 进行快速大纲审查（更快，数据更少）
- 当需要详细场景内容进行分析时使用 include_content=true
- 使用 sort_by="scene_number" 按时间顺序查看故事
- 使用 filter_status 专注于特定工作流阶段（例如，仅草稿场景）
- 大纲为编写相关场景提供必要的上下文

## 参数示例

```json
{
  "include_content": false,
  "sort_by": "scene_number",
  "filter_status": null
}
```

## 输出

返回包含以下内容的 JSON 对象：
- `success`：指示操作是否成功的布尔值
- `total_scenes`：剧本中的场景总数
- `outline`：场景对象数组，每个对象包含：
  - `scene_id`：唯一的场景标识符
  - `title`：场景标题
  - `scene_number`：序列中的场景编号
  - `logline`：简要场景摘要
  - `location`：场景发生地点
  - `time_of_day`：场景的时间
  - `characters`：场景中的角色列表
  - `story_beat`：故事节拍或情节点
  - `duration_minutes`：预估时长
  - `status`：工作流状态
  - `content`：完整的场景内容（仅当 include_content=true 时）
  - `created_at`：创建时间戳
  - `updated_at`：最后更新时间戳
- `filtered_by`：应用的状态过滤器（如果有）
- `sorted_by`：使用的排序顺序
- `message`：人类可读的状态消息

## 错误处理

- 如果上下文中没有剧本管理器，则返回错误
- 如果项目中不存在场景，则返回空大纲
- 检查响应中的 `success` 字段以验证操作是否成功完成
