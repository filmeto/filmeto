---
name: write_single_scene
description: A skill to write and update individual scenes in the screenplay
---

# Single Scene Writing Skill

This skill allows the agent to write and update individual scenes in the project's screenplay. It can create new scenes or modify existing ones with proper formatting and metadata following Hollywood standards.

## Capabilities

- Write new individual scenes with proper screenplay formatting
- Update existing scenes with new content or metadata
- Apply Hollywood-standard screenplay formatting (scene headings, action, character names, dialogue)
- Modify scene metadata (location, time of day, characters, story beat, etc.)
- Preserve existing scene information while updating specific elements
- Follow industry-standard screenplay structure and format

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager to store scenes
- **Unique scene_id**: Each scene must have a unique identifier within the project
- **Content Format**: Scene content should follow Hollywood screenplay format with proper scene headings (use # for headings)
- **Update Behavior**: If a scene with the same `scene_id` exists, it will be updated with new content/metadata while preserving unchanged fields
- **Revision Tracking**: Each update increments the revision_number; created_at and updated_at timestamps are automatically managed

## Input Requirements

Provide these inputs when calling the script via `execute_skill_script`:

- `scene_id` (string, required): Unique identifier (e.g., `scene_001`). Must be unique within the project.
- `title` (string, required): Scene title or heading.
- `content` (string, required): Screenplay content in Hollywood format. Use `#` for scene headings.
- `scene_number` (string, optional): Sequence number like "1", "1A", "2".
- `location` (string, optional): Scene location.
- `time_of_day` (string, optional): DAY, NIGHT, DAWN, DUSK, MORNING, AFTERNOON, EVENING.
- `genre` (string, optional): Genre classification.
- `logline` (string, optional): One-sentence summary.
- `characters` (array, optional): Character names appearing in the scene.
- `story_beat` (string, optional): Story beat or plot point.
- `page_count` (integer, optional): Estimated page count (1 page ≈ 1 minute).
- `duration_minutes` (integer, optional): Estimated duration in minutes.
- `tags` (array, optional): Categorization tags.
- `status` (string, optional, default: "draft"): Scene workflow status.

If required fields are missing in the prompt, infer them: generate a `scene_id` using `scene_###`, create a concise `title`, and draft `content` that matches the requested scene details.

## Usage

The skill can be invoked when users want to create or update specific scenes in the screenplay. It accepts scene details and uses the project's screenplay manager to store the updated scene.

**Best Practices:**
- Use descriptive scene_ids (e.g., `scene_001`, `scene_002`) for easy reference
- Include location and time_of_day in scene content using Hollywood format: `# INT. LOCATION - TIME_OF_DAY`
- Provide logline to summarize the scene's purpose at a glance
- Assign characters array to track which characters appear in each scene
- Use story_beat to indicate the scene's role in the overall story structure
- Set appropriate status to track scene progress through the writing workflow

## Example Arguments

```json
{
  "scene_id": "scene_001",
  "title": "Opening Scene - The Jazz Club",
  "content": "# INT. JAZZ CLUB - NIGHT\n\nSmoke curls through the dim light as a SAXOPHONE wails. JACK MONROE, 40s, weathered face, sits at the bar nursing a whiskey.\n\n**JACK**\n*(to the bartender)*\nAnother one. Make it a double.\n\nThe door swings open. LILA CHEN, 30s, elegant in a red dress, scans the room.",
  "scene_number": "1",
  "location": "JAZZ CLUB",
  "time_of_day": "NIGHT",
  "characters": ["JACK MONROE", "LILA CHEN"],
  "story_beat": "character_introduction",
  "logline": "Jack's routine night is interrupted when a mysterious woman enters the jazz club",
  "duration_minutes": 3,
  "tags": ["intro", "night", "jazz_club"],
  "status": "draft"
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `action`: "created" or "updated" - indicates whether a new scene was created or an existing one was updated
- `scene_id`: The ID of the scene that was created or updated
- `title`: The title of the scene
- `message`: Human-readable status message with details about the operation

## Error Handling

- Returns error if required parameters (scene_id, title, content) are missing
- Returns error if screenplay manager is not available in context
- Returns success=false if scene creation or update fails
- Check the `success` field in the response to verify the operation completed successfully