---
name: write_story_board
description: |-
  Purpose: Create and update storyboard shots.
  Capabilities: Create shot, update shot description, update keyframe context metadata.
  Trigger: When user asks to "add shot", "write storyboard", "update shot description", "edit storyboard shot".
tools:
  - story_board
---

# Write StoryBoard Skill

Use this skill for non-destructive storyboard editing (create/update).

## Create shot

```json
{
  "operation": "create",
  "scene_id": "scene_001",
  "description": "Close-up of protagonist opening a rusted metal box under flickering streetlight.",
  "keyframe_context": {
    "prompt": "cinematic close-up, noir lighting, rain droplets",
    "ability_model": "wanx",
    "reference_images": []
  }
}
```

## Update shot

```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "Updated shot description..."
}
```

## Constraints

- Do not use for deletion; use `delete_story_board`.
- `scene_id` is required.
