---
name: read_screenplay_outline
description: A skill to read the screenplay outline containing all scene summaries
parameters:
  - name: include_content
    type: boolean
    required: false
    default: false
    description: "Whether to include full scene content in the response (default: false - returns metadata only)"
  - name: sort_by
    type: string
    required: false
    default: scene_number
    description: "How to sort the scenes in the outline"
    enum: ["scene_number", "created_at", "updated_at", "title"]
  - name: filter_status
    type: string
    required: false
    description: "Optional filter to only include scenes with a specific status"
    enum: ["draft", "revised", "final", "approved"]
---

# Screenplay Outline Reading Skill

This skill allows the agent to read the complete screenplay outline, which is a structured summary of all scenes in the project. It provides a comprehensive view of the story structure, showing scene summaries in chronological order with key metadata.

## Capabilities

- Read the complete screenplay outline containing all scene summaries
- Retrieve scene metadata including titles, loglines, locations, characters, and story beats
- Sort scenes by scene number, creation date, update date, or title
- Filter scenes by status (draft, revised, final, approved)
- Optionally include full scene content for detailed review
- Provide structured overview of the entire story structure

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager with scenes stored
- **Read-Only**: This skill only reads scenes and does not modify them
- **Empty Outline**: If no scenes exist, returns an empty outline list

## Usage

The skill can be invoked when the screenwriter or director needs to:
- Review the overall story structure
- Understand the scene flow and pacing
- Plan revisions or new scenes
- Identify gaps in the narrative
- Get context before writing specific scenes

**Best Practices:**
- Use include_content=false for quick outline review (faster, less data)
- Use include_content=true when detailed scene content is needed for analysis
- Use sort_by="scene_number" to see the story in chronological order
- Use filter_status to focus on specific workflow stages (e.g., only draft scenes)
- The outline provides essential context for writing connected scenes

## Example Call

```json
{
  "type": "skill",
  "skill": "read_screenplay_outline",
  "args": {
    "include_content": false,
    "sort_by": "scene_number",
    "filter_status": null
  }
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `total_scenes`: Total number of scenes in the screenplay
- `outline`: Array of scene objects, each containing:
  - `scene_id`: Unique scene identifier
  - `title`: Scene title
  - `scene_number`: Scene number in sequence
  - `logline`: Brief scene summary
  - `location`: Where the scene takes place
  - `time_of_day`: Time of day for the scene
  - `characters`: List of characters in the scene
  - `story_beat`: Story beat or plot point
  - `duration_minutes`: Estimated duration
  - `status`: Workflow status
  - `content`: Full scene content (only if include_content=true)
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
- `filtered_by`: Status filter applied (if any)
- `sorted_by`: Sort order used
- `message`: Human-readable status message

## Error Handling

- Returns error if screenplay manager is not available in context
- Returns empty outline if no scenes exist in the project
- Check the `success` field in the response to verify the operation completed successfully
