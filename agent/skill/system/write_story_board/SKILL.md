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

## Shot body writing standard (required)

- Shot body text must follow common storyboard writing style (camera grammar + visual narrative), not a plain static scene description.
- Each `description` should include:
  - framing size (WS/MS/CU/ECU, etc.)
  - camera angle (eye-level/high/low, etc.)
  - camera movement (static/push/pull/pan/track/handheld) and motivation
  - shooting method (subjective/objective POV, focus strategy, long-take/insert intent)
  - subject action and narrative purpose (what the shot needs to communicate)
- Avoid only restating what is visible; state how to shoot it, why this approach is used, and what audience information it delivers.
- Wording should be directly shootable and generation-ready, avoiding vague phrases like "very cinematic."

## Create shot

```json
{
  "operation": "create",
  "scene_id": "scene_001",
  "description": "CU at eye level: protagonist opens a rusted metal box under flickering streetlight; camera starts static, then slowly pushes in with focus pull to the revealed object to emphasize the story reveal.",
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
