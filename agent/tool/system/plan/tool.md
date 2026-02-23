---
name: plan
description: "Manage plans in the project - create, delete, update, get, and list plans"
parameters:
  - name: operation
    description: "Operation type: create, delete, update, get, or list"
    type: string
    required: true
  - name: plan_id
    description: Plan ID. Required for delete, update, and get operations
    type: string
    required: false
  - name: title
    description: Plan title. Used for create and update operations
    type: string
    required: false
  - name: description
    description: Plan description. Used for create and update operations
    type: string
    required: false
  - name: tasks
    description: List of tasks, each task contains fields like id, name, description, title, parameters, needs. Used for create and update operations
    type: array
    required: false
  - name: append_tasks
    description: Additional tasks to append to the plan. Used for update operation
    type: array
    required: false
return_description: Returns operation result with success status, operation details, and plan information
---
