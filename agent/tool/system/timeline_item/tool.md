---
name: timeline_item
description: "Create or edit timeline items, synchronize selection with UI state, and optionally submit image/video/audio generation tasks using prompt + ability."
parameters:
  - name: operation
    description: "Operation type: upsert, create, or edit"
    type: string
    required: false
    default: upsert
  - name: index
    description: "Target timeline item index (1-indexed). Optional for upsert/create."
    type: number
    required: false
  - name: prompt
    description: "Prompt text to store on the target timeline item (tool-scoped when ability is set)."
    type: string
    required: false
  - name: ability
    description: "Ability/tool type for generation, e.g. image/video/audio or text2image/text2video/text2music/text2speak."
    type: string
    required: false
  - name: submit_task
    description: "Whether to immediately submit a generation task for the selected item."
    type: boolean
    required: false
    default: false
  - name: selection_mode
    description: "Optional model selection mode override."
    type: string
    required: false
  - name: server_name
    description: "Optional server override for generation task."
    type: string
    required: false
  - name: model_name
    description: "Optional model override for generation task."
    type: string
    required: false
  - name: selection_tags
    description: "Optional ability selection tags for generation task."
    type: array
    required: false
  - name: min_priority
    description: "Optional minimum model priority for auto selection."
    type: number
    required: false
return_description: Returns selected index, whether a new item was created, whether task was submitted, and effective task parameters.
---
