---
name: screenplay_to_storyboard
description: Convert screenplay into storyboard shots scene-by-scene. For each scene, read screenplay + existing storyboard shots, decide create/update actions, then adjust shots one by one with keyframe generation.
tools:
  - screen_play
  - story_board
---

# Screenplay To Storyboard

This skill converts screenplay to storyboard at scene granularity and shot granularity.
For each single scene, it reads the scene text and existing shots first, then performs incremental shot creation/update.

## Director-Oriented Method

When translating screenplay to storyboard, follow a director-style pipeline instead of simple text conversion:

1. **Dramatic intent first**:
   - Identify scene objective, conflict, emotional turn, and end-state.
   - Prioritize what the audience must understand/feel in this scene.

2. **Visual beat decomposition**:
   - Split scene into visual beats (setup -> development -> turn -> payoff).
   - Each beat should map to one or more shots with clear purpose.

3. **Coverage design, not random shots**:
   - Start from an establishing anchor, then medium coverage, then selective close detail.
   - Use close-ups only for emotional/plot emphasis.
   - Keep a motivated camera language (static, push-in, pan, handheld) tied to scene tension.

4. **Continuity and screen direction**:
   - Preserve 180-degree rule unless intentionally breaking it.
   - Keep eyeline and actor geography stable across adjacent shots.
   - Avoid contradictory staging between old and new shots.

5. **Production practicality**:
   - Prefer executable framing and shot count.
   - Merge redundant shots; split overloaded shots.
   - Keep shot descriptions concise but directable.

## Workflow

1. Read screenplay outline with `screen_play` to get ordered `scene_id` list:

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

3. Process scenes one by one (strict order). For each `scene_id`:
   - Read single screenplay scene:

```json
{
  "type": "tool",
  "tool_name": "screen_play",
  "tool_args": {
    "operation": "get",
    "scene_id": "scene_001"
  }
}
```

   - Read existing storyboard shots of that same scene:

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "list",
    "scene_id": "scene_001"
  }
}
```

4. For the current scene, analyze diff and make a shot plan:
   - Decide which shots should be **created** (missing coverage).
   - Decide which shots should be **updated** (existing shot but description/prompt no longer aligned).
   - Keep stable shot ids when updating; do not recreate unchanged shots.

5. Execute adjustments shot by shot (not batch):
   - **Create path**:

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

   - **Update path**:

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "update",
    "scene_id": "scene_001",
    "shot_id": "scene_001_shot_001",
    "description": "Revised storyboard shot description...",
    "keyframe_context": {
      "prompt": "updated cinematic storyboard frame prompt..."
    }
  }
}
```

6. After each created/updated shot, generate or regenerate keyframe:

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

7. Continue until all scenes are reconciled. Final output must be storyboard shots aligned with screenplay scene-by-scene.

## Scene Analysis Template

For each scene, explicitly extract:

- `scene_goal`: What this scene must achieve in story progression.
- `emotional_curve`: Start emotion -> turn -> end emotion.
- `blocking_core`: Who moves where and relative spatial relations.
- `visual_priority`: Must-show objects/actions/reactions.
- `shot_strategy`: Coverage plan (establishing / two-shot / OTS / close-up / insert / transition).

Use these extracted fields to drive create/update decisions rather than copying screenplay text.

## Shot Design Rules

For each planned shot:

- Define `shot_purpose` (orientation, action clarity, reaction emphasis, reveal, transition).
- Keep one dominant purpose per shot.
- Prefer concrete visual language:
  - framing size (WS/MS/CU/ECU)
  - angle (eye-level/high/low)
  - movement (static/pan/tilt/push/pull/handheld)
  - subject and action
  - lighting/mood keywords
- Avoid vague words like "nice cinematic look" without story function.

## Create vs Update Decision Rules

- **Create shot** when:
  - A screenplay beat has no existing visual coverage.
  - Existing shot count is insufficient for action clarity.
  - New dramatic turn needs dedicated emphasis shot.

- **Update shot** when:
  - Existing shot id still matches beat position but description is weak/outdated.
  - Character blocking, focus, or emotional emphasis changed.
  - Prompt needs stronger visual specificity for generation quality.

- **Keep unchanged** when:
  - Existing shot already matches beat purpose and continuity constraints.

## Per-Scene Execution Checklist

Before moving to next scene, ensure:

1. Every key beat in screenplay has storyboard coverage.
2. Shot order follows narrative logic.
3. Updated/new shots all have regenerated keyframes when needed.
4. No duplicated shots with same purpose unless intentional variation.
5. Shot descriptions are production-usable and visually specific.

## Prompt Pattern

Use this template per shot and fill scene details:

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

If key fields are missing, omit them instead of inventing plot facts.

## Constraints

- Must follow loop: single-scene screenplay read -> single-scene storyboard read -> diff -> per-shot create/update.
- Perform shot operations one by one; do not skip read-before-write for each scene.
- Keep existing good shots; only create or update where needed.
- Always use `story_board` tool for shot creation and image generation; do not use `timeline_item` for this skill.
- Default generation operation is `text2image` unless user explicitly requests `image2image`.
- If scene content is ambiguous, ask minimal clarification or choose conservative coverage instead of inventing major plot facts.
