---
name: story_board
description: "Manage storyboard shots with CRUD plus text2image/image2image keyframe generation"
parameters:
  - name: operation
    description: "Operation type: create, get, update, delete, delete_batch, delete_all, list, text2image, image2image"
    type: string
    required: true
  - name: scene_id
    description: "Scene identifier that owns the shot(s)"
    type: string
    required: false
  - name: shot_id
    description: "Shot identifier under a scene; required for get/update/delete/text2image/image2image. If omitted in create, it is auto-generated"
    type: string
    required: false
  - name: shot_ids
    description: "Shot identifier list for delete_batch"
    type: array
    required: false
  - name: description
    description: "Core storyboard shot description text (stored as shot.md body)"
    type: string
    required: false
  - name: keyframe_context
    description: "Auxiliary metadata for keyframe context (prompt/model/reference/tool)"
    type: object
    required: false
  - name: prompt
    description: "Prompt text for text2image/image2image generation"
    type: string
    required: false
  - name: input_image_path
    description: "Input image path for image2image; falls back to existing shot keyframe if omitted"
    type: string
    required: false
  - name: reference_images
    description: "Reference image paths for text2image guidance"
    type: array
    required: false
  - name: width
    description: "Output image width for generation"
    type: number
    required: false
    default: 1024
  - name: height
    description: "Output image height for generation"
    type: number
    required: false
    default: 1024
  - name: server_name
    description: "Optional generation server name"
    type: string
    required: false
  - name: model
    description: "Optional generation model name"
    type: string
    required: false
return_description: "Returns operation result with shot details, CRUD status, or generated keyframe path"
---
