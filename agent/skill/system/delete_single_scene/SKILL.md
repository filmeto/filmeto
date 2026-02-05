---
name: delete_single_scene
description: A skill to delete individual scenes from the screenplay
---

# Single Scene Deletion Skill

This skill allows the agent to delete individual scenes from the project's screenplay. It provides the ability to remove scenes that are no longer needed or have been replaced.

## Capabilities

- Delete individual scenes by their unique scene_id
- Remove scene files from the screenplay directory
- Verify deletion status
- Handle cases where scene does not exist

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager
- **Valid scene_id**: The scene_id should exist; deletion of non-existent scenes returns success (idempotent)
- **Destructive**: This skill permanently deletes scene files - use with caution

## Input Requirements

Provide these inputs when calling the script via `execute_skill_script`:

- `scene_id` (string, required): Scene identifier (e.g., `scene_001`).

If `scene_id` is missing, ask for it in the final response instead of calling the script.

**IMPORTANT**: Before deleting, consider:
- Confirm with the user if this operation should proceed
- Check if other scenes reference this scene
- Consider if the scene should be archived instead of deleted

## Usage

The skill can be invoked when agents need to remove scenes that are:
- No longer needed in the story
- Duplicates of other scenes
- Replaced by revised versions
- Part of story restructuring

**Best Practices:**
- Always verify the scene_id before deletion
- Consider reading the scene first to confirm it's the correct one
- Warn the user about permanent deletion
- Use with caution as this operation cannot be undone

## Example Arguments

```json
{
  "scene_id": "scene_001"
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `scene_id`: The ID of the scene that was deleted
- `deleted`: Boolean indicating if the scene was actually deleted (false if scene didn't exist)
- `message`: Human-readable status message

Example success response:
```json
{
  "success": true,
  "scene_id": "scene_001",
  "deleted": true,
  "message": "Scene 'scene_001' deleted successfully."
}
```

Example when scene doesn't exist:
```json
{
  "success": true,
  "scene_id": "scene_999",
  "deleted": false,
  "message": "Scene 'scene_999' does not exist. Nothing to delete."
}
```

## Error Handling

- Returns error if scene_id parameter is missing
- Returns error if screenplay manager is not available in context
- Returns success with deleted=false if scene doesn't exist (idempotent operation)
- Check the `success` field in the response to verify the operation completed successfully
