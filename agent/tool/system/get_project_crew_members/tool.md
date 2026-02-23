---
name: get_project_crew_members
description: Get the list of crew members in the current project
parameters:
  - name: project
    description: Project object containing project name and other information
    type: object
    required: false
    default: null
return_description: Returns a list of crew members, each member contains id, name, role, description, soul, skills, model, temperature, max_steps, color, and icon
---
