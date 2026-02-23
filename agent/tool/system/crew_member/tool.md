---
name: crew_member
description: "Manage crew members in the project - create, delete, update, get, and list crew members"
parameters:
  - name: operation
    description: "Operation type: create, delete, update, get, or list"
    type: string
    required: true
  - name: name
    description: Crew member name. Required for delete, update, and get operations
    type: string
    required: false
  - name: data
    description: Crew member data object. Required for create and update operations. Contains fields like name, description, soul, skills, model, temperature, max_steps, color, icon, crew_title, and prompt
    type: object
    required: false
return_description: Returns operation result with success status, operation details, and crew member information
---
