---
name: delete_story_board
description: |-
  Purpose: Delete storyboard shots from a scene.
  Capabilities: Delete one shot, delete a batch, or clear all shots in one scene.
  Trigger: When user asks to "delete shot", "remove storyboard shot", "clear scene storyboard".
tools:
  - story_board
---

# Delete StoryBoard Skill

Use this skill for destructive storyboard cleanup.

## Delete one shot

```json
{
  "operation": "delete",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

## Delete multiple shots

```json
{
  "operation": "delete_batch",
  "scene_id": "scene_001",
  "shot_ids": ["scene_001_shot_001", "scene_001_shot_002"]
}
```

## Delete all shots in scene

```json
{
  "operation": "delete_all",
  "scene_id": "scene_001"
}
```
