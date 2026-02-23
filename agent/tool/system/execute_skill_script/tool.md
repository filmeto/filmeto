---
name: execute_skill_script
description: Execute a pre-defined script from a skill. Can specify full script path directly, or use skill_path + script_name combination.
parameters:
  - name: script_path
    description: Full path to the script (takes priority over skill_path + script_name)
    type: string
    required: false
  - name: skill_path
    description: Path to the skill directory (used when script_path is not provided)
    type: string
    required: false
  - name: script_name
    description: Name of the script to execute (used when script_path is not provided)
    type: string
    required: false
  - name: args
    description: Arguments to pass to the script
    type: object
    required: false
    default: {}
return_description: Returns the execution result from the script (streamed)
---
