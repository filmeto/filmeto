---
name: screen_play
description: "Manage screenplay scenes - create, read, update, delete, and query scenes"
parameters:
  - name: operation
    description: "Operation type: create, get, update, delete, list, get_by_title, get_by_character, get_by_location"
    type: string
    required: true
  - name: scene_id
    description: Unique identifier for the scene. Required for create, get, update, delete operations
    type: string
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
return_description: Returns operation result with success status, scene details, and summary message
---
