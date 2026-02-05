---
name: write_screenplay_outline
description: A skill to generate screenplay outlines and create scenes in the project
---

# Screenplay Outline Writing Skill

This skill allows the agent to generate comprehensive screenplay outlines and create individual scenes in the project's screenplay manager. It can break down a story concept into structured scenes with proper metadata following Hollywood standards.

## Capabilities

- Generate a complete screenplay outline from a concept or idea
- Create individual scenes with proper metadata (location, time of day, characters, etc.)
- Structure scenes following Hollywood screenplay format
- Organize scenes chronologically with proper scene numbers
- Assign characters to appropriate scenes
- Set scene-specific metadata like duration and story beats
- Support genre-specific location templates for Film Noir, Drama, and Action genres

## Constraints

- **Requires Context**: This skill requires a valid ToolContext with access to a screenplay manager
- **Requires Screenplay Manager**: The project must have an initialized screenplay manager to store scenes
- **Scene Limit**: Maximum 10 scenes per outline (based on predefined story structure types)
- **Genre Support**: Specialized location templates available for "Film Noir", "Drama", and "Action" genres
- **Story Structure**: Scenes are generated using predefined story beats (establishing shot, character introduction, conflict setup, rising action, subplot development, character development, plot twist, climax setup, climactic scene, resolution)

## Input Requirements

Provide these inputs when calling the script via `execute_skill_script`:

- `concept` (string, required): Core story idea in 1-2 sentences.
- `genre` (string, optional, default: "General"): "Film Noir", "Drama", or "Action" (case-insensitive). Other values use default location templates.
- `num_scenes` (integer, optional, default: 10): Scene count (1-10). Values above 10 will be capped by the story-structure limit.

If the prompt does not explicitly provide a concept, synthesize a concise 1-2 sentence concept before calling the script.

## Usage

The skill can be invoked when users want to develop a screenplay from scratch or expand an existing concept. It will generate a structured outline and create the corresponding scenes in the project's screenplay manager.

**Best Practices:**
- Provide a clear, concise concept (1-2 sentences describing the core story idea)
- Choose an appropriate genre to get genre-specific location templates
- Use 8-10 scenes for a complete short story structure
- Fewer scenes (5-7) work well for focused narratives

## Example Arguments

```json
{
  "concept": "A detective in 1920s Chicago investigates a series of mysterious disappearances in the jazz district",
  "genre": "Film Noir",
  "num_scenes": 8
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `total_scenes`: Number of scenes generated
- `created_scenes`: List of scene IDs that were successfully created
- `failed_scenes`: List of scene IDs that failed to create (if any)
- `outline_summary`: Array of scene summaries with scene_id and logline for each generated scene
- `message`: Human-readable status message

## Error Handling

- Returns error if `concept` is missing or empty
- Returns error if screenplay manager is not available in context
- Partial success possible: some scenes may be created while others fail
- Failed scenes are listed in `failed_scenes` array with details in the message