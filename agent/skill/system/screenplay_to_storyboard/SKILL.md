---
name: screenplay_to_storyboard
description: Convert screenplay scenes into storyboard timeline items and submit text-to-image generation for each shot. Use when the user asks to transform script/screenplay into storyboard, shot cards, or timeline visual drafts.
tools:
  - screen_play
  - timeline_item
---

# Screenplay To Storyboard

This skill converts screenplay scenes into storyboard cards. Each shot maps to one timeline item, and each timeline item triggers image generation.

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

4. For each shot, create/edit one timeline item and submit image generation:

```json
{
  "type": "tool",
  "tool_name": "timeline_item",
  "tool_args": {
    "operation": "create",
    "prompt": "cinematic storyboard frame, ...",
    "ability": "text2image",
    "submit_task": true
  }
}
```

5. Ensure all shots are processed in scene order. The last processed item should remain selected.

## Prompt Pattern

Use this template and fill scene details:

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

If key fields are missing, omit them instead of inventing plot facts.

## Constraints

- One timeline item per shot.
- Always set `ability` to `text2image` for storyboard generation unless user requests another ability.
- Keep execution consistent with UI behavior by using `timeline_item` tool only (do not mutate timeline files directly).
