---
name: rewrite_story_board
description: |-
  Purpose: Rewrite existing storyboard shot descriptions based on user direction.
  Capabilities: Retrieve shot then update only description and/or keyframe context.
  Trigger: When user asks to "rewrite shot", "change shot tone", "make shot description more detailed".
tools:
  - story_board
---

# Rewrite StoryBoard Skill

Use this skill to revise existing shots while keeping shot identity stable.

## Recommended flow

1. Read current shot:
```json
{
  "operation": "get",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

2. Update rewritten result:
```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "Rewritten shot description..."
}
```
