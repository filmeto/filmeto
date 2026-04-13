---
name: rewrite_story_board
description: |-
  Purpose: 根据用户指令重写已有分镜镜头描述。
  Capabilities: 先读取镜头，再仅更新描述和/或关键帧上下文。
  Trigger: 当用户提出“重写镜头”、“调整镜头语气”、“把镜头描述写得更细”时触发。
tools:
  - story_board
---

# 重写分镜 Skill

用于在不改变镜头身份的前提下，重写已有镜头内容。

## 推荐流程

1. 读取当前镜头：
```json
{
  "operation": "get",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

2. 写回重写结果：
```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "重写后的镜头描述..."
}
```
