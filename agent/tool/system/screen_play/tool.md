---
name: screen_play
description: "Manage screenplay scenes - create, read, update, delete, list, outline, and query scenes"
parameters:
  - name: operation
    description: "Operation type: create, get, update, delete, delete_all, delete_batch, list, outline, get_by_title, get_by_character, get_by_location"
    type: string
    required: true
  - name: scene_id
    description: Unique identifier for the scene. Required for create, get, update, delete operations
    type: string
    required: false
  - name: scene_ids
    description: List of scene identifiers for delete_batch operation
    type: array
    required: false
  - name: title
    description: Scene title. Used for create, update, get_by_title operations
    type: string
    required: false
  - name: content
    description: Scene content in markdown format. Used for create, update operations
    type: string
    required: false
  - name: metadata
    description: Scene metadata dictionary. Contains scene_number, location, time_of_day, genre, logline, characters, story_beat, page_count, duration_minutes, tags, status, revision_number. Used for create, update operations
    type: object
    required: false
  - name: character_name
    description: Character name to search for. Used for get_by_character operation
    type: string
    required: false
  - name: location
    description: Location to search for (partial match). Used for get_by_location operation
    type: string
    required: false
  - name: include_content
    description: Include full scene content in outline response. Used for outline operation
    type: boolean
    required: false
    default: false
  - name: sort_by
    description: Sort order for outline. Used for outline operation. Values: scene_number, created_at, updated_at, title
    type: string
    required: false
    default: scene_number
  - name: filter_status
    description: Filter by status for outline. Used for outline operation. Values: draft, revised, final, approved
    type: string
    required: false
return_description: Returns operation result with success status, scene details, and summary message
---
