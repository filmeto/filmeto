---
name: delete_story_board
description: |-
  Purpose: 删除场景中的分镜镜头。
  Capabilities: 删除单个镜头、批量删除镜头、清空某场景下全部镜头。
  Trigger: 当用户提出“删除镜头”、“移除分镜镜头”、“清空场景分镜”时触发。
tools:
  - story_board
---

# 删除分镜 Skill

用于分镜的删除类操作。

## 删除单个镜头

```json
{
  "operation": "delete",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

## 批量删除镜头

```json
{
  "operation": "delete_batch",
  "scene_id": "scene_001",
  "shot_ids": ["scene_001_shot_001", "scene_001_shot_002"]
}
```

## 删除场景全部镜头

```json
{
  "operation": "delete_all",
  "scene_id": "scene_001"
}
```
