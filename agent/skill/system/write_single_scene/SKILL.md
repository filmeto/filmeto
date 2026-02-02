---
name: write_single_scene
description: A skill to write and update individual scenes in the screenplay
parameters:
  - name: scene_id
    type: string
    required: true
    description: Unique identifier for the scene (e.g., scene_001, scene_002). Must be unique within the project.
  - name: title
    type: string
    required: true
    description: Title or heading for the scene (typically describes the scene's main event)
  - name: content
    type: string
    required: true
    description: The screenplay content in Hollywood format (scene headings, action, dialogue). Use markdown formatting with # for scene headings.
  - name: scene_number
    type: string
    required: false
    description: Scene number in the screenplay sequence (e.g., "1", "1A", "2")
  - name: location
    type: string
    required: false
    description: Location of the scene (e.g., "COFFEE SHOP", "CITY STREET", "INT. APARTMENT")
  - name: time_of_day
    type: string
    required: false
    description: Time of day for the scene. Standard values DAY, NIGHT, DAWN, DUSK, MORNING, AFTERNOON, EVENING
    enum: ["DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "AFTERNOON", "EVENING"]
  - name: genre
    type: string
    required: false
    description: Genre classification for the scene (e.g., "Drama", "Comedy", "Action", "Thriller")
  - name: logline
    type: string
    required: false
    description: Brief one-sentence summary of what happens in the scene
  - name: characters
    type: array
    required: false
    description: List of character names appearing in the scene (e.g., ["DETECTIVE", "SUSPECT"])
  - name: story_beat
    type: string
    required: false
    description: Story beat or plot point for the scene (e.g., "inciting_incident", "climax", "resolution")
  - name: page_count
    type: integer
    required: false
    minimum: 1
    description: Estimated page count for the scene (1 page ≈ 1 minute of screen time)
  - name: duration_minutes
    type: integer
    required: false
    minimum: 1
    description: Estimated duration in minutes
  - name: tags
    type: array
    required: false
    description: Tags for categorizing the scene (e.g., ["action", "outdoor", "night"])
  - name: status
    type: string
    required: false
    default: draft
    description: Status of the scene workflow
    enum: ["draft", "revised", "final", "approved"]
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

## Usage

The skill can be invoked when users want to create or update specific scenes in the screenplay. It accepts scene details and uses the project's screenplay manager to store the updated scene.

**Best Practices:**
- Use descriptive scene_ids (e.g., `scene_001`, `scene_002`) for easy reference
- Include location and time_of_day in scene content using Hollywood format: `# INT. LOCATION - TIME_OF_DAY`
- Provide logline to summarize the scene's purpose at a glance
- Assign characters array to track which characters appear in each scene
- Use story_beat to indicate the scene's role in the overall story structure
- Set appropriate status to track scene progress through the writing workflow

## Example Call

```json
{
  "type": "skill",
  "skill": "write_single_scene",
  "args": {
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