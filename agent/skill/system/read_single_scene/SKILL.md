---
name: read_single_scene
description: A skill to read and retrieve individual scenes from the screenplay
parameters:
  - name: scene_id
    type: string
    required: true
    description: Unique identifier for the scene to read (e.g., scene_001, scene_002)
  - name: include_content
    type: boolean
    required: false
    default: true
    description: Whether to include the full scene content in the response
  - name: include_metadata
    type: boolean
    required: false
    default: true
    description: Whether to include scene metadata (location, time, characters, etc.)
---

# Single Scene Reading Skill

This skill allows the agent to read and retrieve individual scenes from the project's screenplay. It provides access to scene content and metadata for analysis, review, or as context for further creative work.

## Capabilities

- Read individual scenes by their unique scene_id
- Retrieve scene content in Hollywood screenplay format
- Access scene metadata including location, time of day, characters, story beat, etc.
- Filter response to include only content or only metadata as needed
- Provide structured scene information for analysis or revision

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager with scenes stored
- **Valid scene_id**: The scene_id must exist in the screenplay; otherwise returns an error
- **Read-Only**: This skill only reads scenes and does not modify them

## Usage

The skill can be invoked when agents need to review existing scenes, analyze scene structure, or use scene content as context for writing or revising other scenes.

**Best Practices:**
- Use when the screenwriter or director needs to review a specific scene
- Useful for analyzing scene structure, dialogue, or action before making revisions
- Can be used to reference previous scenes when writing sequels or connected scenes
- Set include_content=false when only metadata is needed (faster response)
- Set include_metadata=false when only the scene text is needed

## Example Call

```json
{
  "type": "skill",
  "skill": "read_single_scene",
  "args": {
    "scene_id": "scene_001",
    "include_content": true,
    "include_metadata": true
  }
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `scene_id`: The ID of the scene that was read
- `title`: The title of the scene
- `content`: The scene content (if include_content=true)
- `metadata`: Object containing scene metadata (if include_metadata=true):
  - `scene_number`: Scene number in the screenplay
  - `location`: Location of the scene
  - `time_of_day`: Time of day for the scene
  - `genre`: Genre classification
  - `logline`: Brief summary of the scene
  - `characters`: List of characters in the scene
  - `story_beat`: Story beat or plot point
  - `page_count`: Estimated page count
  - `duration_minutes`: Estimated duration
  - `tags`: Categorization tags
  - `status`: Workflow status (draft, revised, final, approved)
  - `revision_number`: Current revision number
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
- `message`: Human-readable status message

## Error Handling

- Returns error if scene_id parameter is missing
- Returns error if the specified scene_id does not exist in the screenplay
- Returns error if screenplay manager is not available in context
- Check the `success` field in the response to verify the operation completed successfully
