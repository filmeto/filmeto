---
name: write_story_board
description: |-
  Purpose: 创建和更新分镜镜头。
  Capabilities: 新建镜头、更新镜头描述、更新关键帧上下文元数据。
  Trigger: 当用户提出“新增镜头”、“写分镜”、“修改镜头描述”、“编辑分镜镜头”时触发。
tools:
  - story_board
---

# 写分镜 Skill

用于分镜的非删除类编辑（创建/更新）。

## 创建镜头

```json
{
  "operation": "create",
  "scene_id": "scene_001",
  "description": "主角在闪烁街灯下打开生锈金属盒的特写镜头。",
  "keyframe_context": {
    "prompt": "cinematic close-up, noir lighting, rain droplets",
    "ability_model": "wanx",
    "reference_images": []
  }
}
```

## 更新镜头

```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "更新后的镜头描述..."
}
```

## 约束

- 不用于删除操作；删除请使用 `delete_story_board`。
- `scene_id` 必填。
