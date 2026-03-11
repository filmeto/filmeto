---
name: delete_screen_play
description: |-
  Purpose: Delete multiple or all screenplay scenes from the project for major restructuring or fresh start.
  Capabilities: Delete all scenes at once or selectively delete specific scenes by IDs, verify deletion status.
  Trigger: When user says "delete screenplay", "clear screenplay", "remove scenes", "delete all scenes", or wants to start fresh.
---

# Screenplay Deletion Skill

This skill deletes screenplay scenes from the project. Two modes: delete all scenes, or delete specific scenes by IDs.

## Execution Priority (Critical)

**Execute the delete immediately. Do NOT:**
- Read the full screenplay or list all scenes before deleting (unless you need scene_ids for partial mode)
- Ask the user to confirm again—phrases like "delete screenplay" or "clear screenplay" are explicit intent; proceed to execute
- Spend steps on warnings or backup suggestions before calling the skill

**Do:**
- When user says delete/clear screenplay (all): call `execute_skill_script` with `delete_screen_play` and `{"delete_mode": "all"}` in the same or next step
- When user wants specific scenes removed: obtain scene_ids (e.g. from a prior list or user message), then call with `delete_mode: "partial"` and `scene_ids`
- Report the script result (deleted_count, message) after execution

## Capabilities

- Delete all screenplay scenes in the project (full cleanup)
- Delete specific scenes by their scene_ids (selective cleanup)
- Handle cases where scenes do not exist

## Constraints

- **Requires Context**: Valid ToolContext with screenplay manager
- **Destructive**: Permanently deletes scene files

## Input Requirements

Call via `execute_skill_script` with:

### Full Deletion (delete all scenes)
- `delete_mode` (string): `"all"`
- No other parameters required

### Partial Deletion (delete specific scenes)
- `delete_mode` (string): `"partial"`
- `scene_ids` (list of strings, required): e.g. `["scene_001", "scene_002"]`

If user said "delete all" / "clear screenplay" and parameters are clear, do not ask for confirmation—invoke the script. Only ask when mode or scene_ids are genuinely ambiguous.

## Example Arguments

### Delete all scenes:
```json
{
  "delete_mode": "all"
}
```

### Delete specific scenes:
```json
{
  "delete_mode": "partial",
  "scene_ids": ["scene_001", "scene_002", "scene_003"]
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `delete_mode`: The mode used ("all" or "partial")
- `deleted_count`: Number of scenes actually deleted
- `deleted_scene_ids`: List of scene IDs that were deleted
- `message`: Human-readable status message

Example success response (full deletion):
```json
{
  "success": true,
  "delete_mode": "all",
  "deleted_count": 10,
  "deleted_scene_ids": ["scene_001", "scene_002", "..."],
  "message": "Successfully deleted all 10 screenplay scenes."
}
```

Example success response (partial deletion):
```json
{
  "success": true,
  "delete_mode": "partial",
  "deleted_count": 3,
  "deleted_scene_ids": ["scene_001", "scene_002", "scene_003"],
  "message": "Successfully deleted 3 screenplay scenes."
}
```

Example when no scenes exist:
```json
{
  "success": true,
  "delete_mode": "all",
  "deleted_count": 0,
  "deleted_scene_ids": [],
  "message": "No screenplay scenes found. Nothing to delete."
}
```

## Error Handling

- Returns error if `delete_mode` is missing or invalid
- Returns error if `scene_ids` is missing for partial mode
- Returns error if screenplay manager is not available in context
- Returns success with deleted_count=0 if no scenes exist to delete
