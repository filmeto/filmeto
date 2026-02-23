---
name: video_timeline
description: "Manage video timeline items - add, delete, move, and update timeline cards. Timeline indices are 1-indexed."
parameters:
  - name: operation
    description: "Operation type: add, delete, move, update, list, or get"
    type: string
    required: true
  - name: index
    description: Timeline item index (1-indexed). Required for delete, move, update, get operations
    type: number
    required: false
  - name: to_index
    description: Target position index (1-indexed). Required for move operation
    type: number
    required: false
  - name: image_path
    description: Path to image file. Used for update operation
    type: string
    required: false
  - name: video_path
    description: Path to video file. Used for update operation
    type: string
    required: false
return_description: Returns operation result with success status, operation details, and current timeline info
---
