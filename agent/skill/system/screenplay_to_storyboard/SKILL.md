---
name: screenplay_to_storyboard
description: Convert screenplay scenes into storyboard timeline items and submit text-to-image generation for each shot. Use when the user asks to transform script/screenplay into storyboard, shot cards, or timeline visual drafts.
tools:
  - screen_play
  - story_board
---

# Screenplay To Storyboard

This skill converts screenplay scenes into storyboard shots. Each shot is created in storyboard data, then triggers keyframe generation.

## Workflow

1. Read screenplay outline with `screen_play`:

```json
{
  "type": "tool",
  "tool_name": "screen_play",
  "tool_args": {
    "operation": "outline",
    "include_content": true,
    "sort_by": "scene_number"
  }
}
```

2. If no scenes exist, stop and tell the user to create screenplay scenes first.

3. Build shot prompts from scenes:
- Prefer `logline`, `location`, `time_of_day`, `characters`, `story_beat`, and `content`.
- Default to one shot per scene unless the user asks for multiple shots.
- Keep prompts visual and concise.

4. For each shot, create one storyboard shot:

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "create",
    "scene_id": "scene_001",
    "description": "Storyboard shot for scene ...",
    "keyframe_context": {
      "prompt": "cinematic storyboard frame, ..."
    }
  }
}
```

5. Then generate keyframe for that shot with `story_board`:

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "text2image",
    "scene_id": "scene_001",
    "shot_id": "scene_001_shot_001",
    "prompt": "cinematic storyboard frame, ...",
    "width": 1024,
    "height": 1024
  }
}
```

6. Ensure all shots are processed in scene order, and each generated image is bound to its corresponding storyboard shot.

## Prompt Pattern

Use this template and fill scene details:

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

If key fields are missing, omit them instead of inventing plot facts.

## Constraints

- One storyboard shot per planned shot.
- Always use `story_board` tool for shot creation and image generation; do not use `timeline_item` for this skill.
- Default generation operation is `text2image` unless user explicitly requests `image2image`.
