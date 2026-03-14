---
name: rewrite_screenplay
description: |-
  Purpose: Rewrite screenplay content according to user instructions while preserving Hollywood format and ensuring instruction compliance.
  Capabilities: Apply user-directed edits to one scene or the whole screenplay; preserve metadata and format; output only rewritten content.
  Trigger: When user wants to "rewrite", "edit", "change", "modify" the screenplay by instruction, or "make the scene...", "update the dialogue to...".
---

# Rewrite Screenplay Skill

This skill rewrites screenplay scenes according to explicit user instructions. It reads existing content, applies the requested changes via LLM, and writes back only the revised screenplay content so that instructions are followed and format is preserved.

## Capabilities

- Rewrite one scene or the entire screenplay based on a clear user instruction
- Preserve Hollywood screenplay format (scene headings, action, character names, dialogue)
- Preserve scene metadata (location, characters, logline, etc.) unless the instruction says otherwise
- Ensure the output strictly follows the user's instruction (tone, plot change, dialogue edit, etc.)

## Constraints

- **Requires Context**: Valid ToolContext with screenplay manager and LLM service
- **Instruction Required**: `instruction` must be provided and describe what to change
- **Scope**: Use `scene_id` for a single scene or omit/use "all" for the whole screenplay
- **Output**: The skill uses the LLM to produce only rewritten content; no commentary in the saved content

## Input Requirements

When calling via `execute_skill_script`:

- `instruction` (string, required): The user's rewrite directive (e.g. "Make the dialogue more tense", "Change the location to a beach", "Shorten the scene by half").
- `scene_id` (string, optional): If set, only this scene is rewritten. If omitted or empty, all scenes are rewritten.
- `scope` (string, optional): Alternative to scene_id. Use "all" to rewrite every scene; if not provided and scene_id is not set, defaults to "all".

If `instruction` is missing, the skill returns an error. Infer nothing for instruction; the user must state what to change.

## Usage

Invoke when the user asks to modify the screenplay by description (e.g. "Rewrite the opening to be darker", "Make the dialogue in scene_002 more natural", "Change all scenes to take place at night"). The skill will read the relevant scene(s), call the LLM with the instruction, and update the screenplay so that the result complies with the instruction.

**Best practices:**
- Pass a clear, concrete instruction so the model can follow it exactly.
- Use `scene_id` when only one scene should change; leave scope broad for global changes (tone, setting, style).

## Example Arguments

```json
{
  "instruction": "Make the dialogue in this scene more tense and add a brief conflict between the two characters.",
  "scene_id": "scene_001"
}
```

```json
{
  "instruction": "Shorten every scene by removing redundant action lines; keep all dialogue.",
  "scope": "all"
}
```

## Output

Returns a JSON object:

- `success`: Boolean
- `updated_scenes`: List of scene_ids that were rewritten
- `message`: Human-readable summary
- On error: `error`, `message` with details

## Error Handling

- Missing `instruction` returns error.
- No screenplay manager or LLM in context returns error.
- Missing scene_id when scope is a single scene returns error.
- LLM or update failures are reported in the response.
