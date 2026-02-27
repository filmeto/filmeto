---
name: delete_screen_play
description: A skill to delete screenplay scenes from the project - supports full deletion or partial scene deletion
---

# Screenplay Deletion Skill

This skill allows the agent to delete screenplay scenes from the project. It supports two modes: complete deletion of all scenes, or selective deletion of specific scenes.

## Capabilities

- Delete all screenplay scenes in the project (full cleanup)
- Delete specific scenes by their scene_ids (selective cleanup)
- Verify deletion status
- Handle cases where scenes do not exist

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager
- **Destructive Operation**: This skill permanently deletes scene files - use with extreme caution

## Input Requirements

Provide these inputs when calling the script via `execute_skill_script`:

### Full Deletion (delete all scenes)
- `delete_mode` (string): Must be `"all"` to delete all scenes
- No other parameters required

### Partial Deletion (delete specific scenes)
- `delete_mode` (string): Must be `"partial"` to delete specific scenes
- `scene_ids` (list of strings, required): List of scene identifiers to delete (e.g., `["scene_001", "scene_002"]`)

If required parameters are missing, ask for them in the final response instead of calling the script.

## When to Use This Skill

**This is a DANGEROUS operation. Only use this skill when:**

1. The current screenplay completely fails to meet requirements and needs to be rewritten from scratch
2. There are fundamental story structure problems that cannot be fixed by editing
3. The user explicitly requests to clear the screenplay
4. A major plot revision requires removing multiple scenes

**Do NOT use this skill for:**
- Minor scene adjustments (use `update` operation instead)
- Deleting a single scene (use `delete_single_scene` skill instead)
- Simple dialogue or description changes (use `update` operation instead)

## Important Warnings

**Before executing this skill:**
1. Always confirm with the user that they want to proceed with deletion
2. Clearly state which scenes will be deleted (all or specific list)
3. Warn that this operation cannot be undone
4. Consider suggesting to backup the screenplay first

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
