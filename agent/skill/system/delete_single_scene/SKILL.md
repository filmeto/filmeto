---
name: delete_single_scene
description: |-
  Purpose: Delete individual scenes from the screenplay that are no longer needed.
  Capabilities: Remove scenes by scene_id, verify deletion status, handle non-existent scenes gracefully.
  Trigger: Explicit user commands like "delete scene", "remove scene", "delete scene_001", "remove scene 3", "删除场景", etc.
---

# Single Scene Deletion Skill

This skill allows the agent to delete individual scenes from the project's screenplay based on explicit user instructions.

## Intent Recognition

This skill should be invoked when the user explicitly requests scene deletion with clear intent:

**Trigger Patterns (English):**
- "delete scene [scene_id/scene number]"
- "remove scene [scene_id/scene number]"
- "delete scene number X"
- "remove scene X from the screenplay"
- "delete the [first/second/third...] scene"

**Trigger Patterns (Chinese):**
- "删除场景 [场景ID/场景编号]"
- "移除场景 [场景ID/场景编号]"
- "删除第X个场景"
- "把场景X删掉"

## Capabilities

- Delete individual scenes by their unique scene_id
- Parse scene identifiers from natural language (e.g., "scene_001", "scene 1", "第一个场景")
- Remove scene files from the screenplay directory
- Verify deletion status
- Handle cases where scene does not exist

## Execution Flow

When handling a scene deletion request, follow these steps:

### Step 1: Extract scene_id from User Input
Parse the user's command to identify the scene identifier:
- If user provides explicit scene_id (e.g., "scene_001", "scene_3"): Use it directly
- If user refers to scene by number (e.g., "scene 1", "第1个场景"): Convert to scene_id format (scene_001)
- If user says "first scene", "second scene": Map ordinal to actual scene_id from the screenplay
- **If scene_id cannot be determined**: Ask user to specify which scene to delete

### Step 2: Confirm with User (Optional but Recommended)
Before executing deletion, confirm with user:
- "Are you sure you want to delete scene [scene_id]? This action cannot be undone."
- If user confirms, proceed to Step 3

### Step 3: Execute Deletion
Call the skill script with the extracted `scene_id` parameter:
```python
execute_skill_script("delete_single_scene", {"scene_id": "scene_001"})
```

### Step 4: Report Result
Parse the response and inform the user:
- If success=true and deleted=true: "Scene 'scene_001' has been deleted successfully."
- If success=true and deleted=false: "Scene 'scene_999' does not exist. Nothing to delete."
- If success=false: Report the error message to user

## Constraints
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
