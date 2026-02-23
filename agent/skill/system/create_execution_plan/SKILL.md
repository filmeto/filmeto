---
name: create_execution_plan
description: Creates an execution plan for film production projects using the plan tool
---
# Execution Plan Creation Skill

This skill creates an execution plan for film production projects using the plan tool. It allows producers and other crew members to define and track project milestones, tasks, and responsibilities.

## Capabilities

- Create structured execution plans with named tasks and dependencies
- Assign tasks to specific crew members using valid titles
- Define task parameters and dependencies between tasks
- Track project milestones and responsibilities

## Important Notes for Plan Creation

When creating a plan, you must provide tasks in the following JSON format:

Each task must include: id, name, description, title, needs, parameters.

The title MUST be one of the following valid crew member titles:
- producer
- director
- screenwriter
- cinematographer
- editor
- sound_designer
- vfx_supervisor
- storyboard_artist

Using any other title (such as 'system', 'user', 'assistant', etc.) will cause the task to fail.

Tasks can have dependencies defined in the 'needs' field, which should contain an array of other task IDs that must be completed before this task can begin.

## Input Requirements

Provide these inputs when calling the script via `execute_skill_script`:

- `plan_name` (string, required): Name of the execution plan.
- `description` (string, optional): Description of the plan.
- `tasks` (array, optional): Task list for the plan. If not provided, create a minimal, reasonable task list from the prompt.
  - Each task should include: `id`, `name`, `description`, `title`, `needs`, `parameters`.
  - `title` must be one of the valid crew member titles listed above.

If `plan_name` is not explicitly provided, derive a concise name from the prompt.

## Usage

The skill can be invoked when users want to create a structured execution plan for a film production project. The plan will be created with the specified tasks assigned to appropriate crew members.

## Execution Context

This skill supports both direct script execution and in-context execution via the SkillExecutor. When executed through the SkillExecutor, it receives a SkillContext object containing project and workspace information, and arguments are passed directly to the execute function.

## Example Arguments

```json
{
  "plan_name": "Pre-production Schedule",
  "description": "Detailed schedule for pre-production activities",
  "tasks": [
    {
      "id": "task1",
      "name": "Script Finalization",
      "description": "Complete final revisions to the script",
      "title": "screenwriter",
      "needs": [],
      "parameters": {}
    },
    {
      "id": "task2",
      "name": "Location Scouting",
      "description": "Find and secure filming locations",
      "title": "director",
      "needs": ["task1"],
      "parameters": {}
    },
    {
      "id": "task3",
      "name": "Casting",
      "description": "Hold auditions and select cast members",
      "title": "director",
      "needs": ["task1"],
      "parameters": {}
    }
  ]
}
```

## Output

Returns a JSON object containing:
- `success`: Boolean indicating if the operation succeeded
- `message`: Human-readable status message
- `plan_id`: Unique identifier for the created plan
- `plan_name`: Name of the created plan
- `project`: Name of the project the plan belongs to