---
name: todo_write
description: "Create and manage structured task lists for your current coding session. This tool helps the AI assistant track progress and organize complex tasks. IMPORTANT CONSTRAINTS: 1) TODO planning must be based on currently available tools; 2) Do NOT include the todo_write tool itself in the TODO list."
parameters:
  - name: todos
    description: "Array of TODO items, each containing content (task description), status (pending/in_progress/completed), and activeForm (present continuous form). Note: Plan tasks based on available tools only, do NOT include using todo_write as a task."
    type: array
    required: true
return_description: Returns the updated state of the task list
---
