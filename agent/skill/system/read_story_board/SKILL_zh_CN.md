---
name: read_story_board
description: |-
  Purpose: 读取场景分镜镜头，包含镜头描述、关键帧路径和关键帧上下文信息。
  Capabilities: 按场景列出全部镜头，或按镜头 ID 读取单个镜头。
  Trigger: 当用户提出“读取分镜”、“查看镜头”、“列出分镜镜头”、“查看镜头详情”时触发。
tools:
  - story_board
---

# 读取分镜 Skill

用于只读查看分镜数据，不修改内容。

## 操作

- 列出场景全部镜头：
```json
{
  "operation": "list",
  "scene_id": "scene_001"
}
```

- 读取单个镜头：
```json
{
  "operation": "get",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

## 说明

- 需要有效项目上下文和 storyboard manager。
- `scene_id` 必填。
- 返回核心字段：`shot_no`、`description`、`keyframe_path`、`keyframe_context`。
