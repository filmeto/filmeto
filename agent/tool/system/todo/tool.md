---
name: todo
description: "Manage TODO lists for tracking progress during complex tasks - create, delete, update, get, and list items"
parameters:
  - name: operation
    description: "Operation type: create, delete, update, get, or list"
    type: string
    required: true
  - name: todos
    description: "Array of TODO items for create operation, each containing content (task description), status (pending/in_progress/completed), and activeForm (present continuous form)"
    type: array
    required: false
  - name: todo_id
    description: "TODO item ID for delete, update, and get operations"
    type: string
    required: false
  - name: title
    description: "TODO title for delete, update, and get operations (alternative to todo_id)"
    type: string
    required: false
  - name: content
    description: "New content/description for update operation"
    type: string
    required: false
  - name: status
    description: "New status for update operation: pending, in_progress, completed, failed, or blocked"
    type: string
    required: false
  - name: activeForm
    description: "New present continuous form for update operation"
    type: string
    required: false
return_description: Returns operation result with success status, operation details, and TODO list information
---
