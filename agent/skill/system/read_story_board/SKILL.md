---
name: read_story_board
description: |-
  Purpose: Read storyboard shots for a scene, including shot description, keyframe path, and keyframe context.
  Capabilities: List all shots in a scene or read one shot by id.
  Trigger: When user asks to "read storyboard", "show shots", "list storyboard shots", "view shot details".
tools:
  - story_board
---

# Read StoryBoard Skill

Use this skill to inspect storyboard data without changing it.

## Operations

- List scene shots:
```json
{
  "operation": "list",
  "scene_id": "scene_001"
}
```

- Get one shot:
```json
{
  "operation": "get",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

## Notes

- Requires valid project context with storyboard manager.
- `scene_id` is required.
- Returns shot core fields: `shot_no`, `description`, `keyframe_path`, `keyframe_context`.
