---
name: execute_generated_code
description: Execute dynamically generated Python code
parameters:
  - name: code
    description: Python code to execute
    type: string
    required: true
  - name: args
    description: Arguments to pass to the code
    type: object
    required: false
    default: {}
return_description: Returns the execution result from the generated code (streamed)
---
