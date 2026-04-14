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

## Shot rewrite requirements (required)

- Rewritten shot body should follow common storyboard prose, not only depict what appears in frame.
- Ensure these elements are explicit when missing:
  - framing and camera angle
  - camera movement path/rhythm (e.g., slow push, lateral track, follow)
  - shooting method (subjective/objective POV, focus handling, long-take vs cut intent)
  - subject action, narrative function, and emotional direction
- Preserve the original narrative intent and scene facts; improve directability and production usefulness.

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
  "description": "MS over-shoulder from side rear during dialogue; camera holds, then slowly tracks to the listener's reaction and pauses on key line, using objective POV with light focus shift to underline power change."
}
```
