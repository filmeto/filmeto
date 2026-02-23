---
name: execute_skill
description: Execute a skill through ReAct-based chat stream
parameters:
  - name: skill_name
    description: Name of the skill to execute
    type: string
    required: true
  - name: prompt
    description: Task prompt including required details
    type: string
    required: true
return_description: Returns the execution result from the skill (streamed)
---
