---
name: create_plan
description: Create a plan execution for the current project
parameters:
  - name: title
    description: Plan title
    type: string
    required: true
    default: Untitled Plan
  - name: description
    description: Plan description
    type: string
    required: false
    default: No description provided
  - name: tasks
    description: List of tasks, each task contains fields like id, name, description, title, parameters, needs
    type: array
    required: true
    default: []
return_description: Returns the created plan details including plan ID, title, description, task list, creation time, and status
---
