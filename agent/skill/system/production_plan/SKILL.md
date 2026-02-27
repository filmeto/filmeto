---
name: production_plan
description: Creates a comprehensive film production plan by analyzing crew capabilities, breaking down tasks, and scheduling crew member assignments
tools:
  - crew_member
  - plan
---
# Film Production Plan Creation

## CRITICAL: Multi-Step Execution Requirement

This skill requires **MULTIPLE TOOL CALLS** in sequence. You MUST complete ALL steps before providing a final response.

**MANDATORY EXECUTION CHECKLIST** - Do NOT finish until ALL are complete:
- [ ] Step 1: Gather crew member information (see Step 1 details below)
- [ ] Step 2: Analyze the crew information and user requirements
- [ ] Step 3: Call `plan` tool with `create` operation to store the production plan

**COMPLETION CRITERIA**: This task is ONLY complete when:
- You have successfully called the `plan` tool with `create` operation
- The plan was created successfully (you received a success response with a plan_id)
- You have provided a summary of the created plan

**DO NOT** stop after calling only `crew_member`. You MUST continue to call `plan` tool.

---

## Step 1: Gather Crew Member Information

**IMPORTANT**: Check if crew member information is already provided in the input before calling `crew_member` tool.

### Option A: Crew Members Already Provided in Input

If the input already contains crew member information (under `crew_members` parameter or in the prompt context), **DO NOT** call `crew_member` tool. Instead, use the provided information directly.

Look for crew member data in:
- The `crew_members` parameter in the input
- A "Team Context" or "Fellow Crew Members" section in the prompt

Example of provided crew member info:
```
- **Alex Chen** (role: director)
  - Description: Responsible for creative vision...
  - Skills: scene_breakdown, shot_planning
- **Jordan Lee** (role: screenwriter)
  - Description: Develops screenplay...
  - Skills: script_writing, character_development
```

### Option B: Crew Members NOT Provided - Call crew_member Tool

If crew member information is **NOT** provided in the input, use the `crew_member` tool with `list` operation to:
- Get all available crew members
- Understand each member's role, skills, and capabilities
- Identify which crew member is best suited for each type of task

**Example tool call:**
```json
{
  "type": "tool",
  "tool_name": "crew_member",
  "tool_args": {
    "operation": "list"
  }
}
```

---

## Step 2: Analyze and Break Down the Task

After gathering crew information (either from input or from tool call), analyze the user's production requirements:
- Decompose the overall production goal into specific, actionable tasks
- Identify task dependencies (which tasks must complete before others can start)
- Match each task to the most appropriate crew member based on their role and skills

---

## Step 3: Create and Store the Production Plan

Finally, use the `plan` tool with `create` operation to store the production plan:
- Give the plan a descriptive title based on the production goal
- Write a clear description of what the plan covers
- Include all tasks with proper:
  - `id`: Unique task identifier (e.g., "task_1", "task_2")
  - `name`: Brief task name
  - `description`: Detailed task description
  - `title`: Crew member role responsible (e.g., producer, director, screenwriter)
  - `needs`: List of task IDs this task depends on
  - `parameters`: Additional task parameters (can be empty {})

**Example tool call:**
```json
{
  "type": "tool",
  "tool_name": "plan",
  "tool_args": {
    "operation": "create",
    "title": "Pre-Production Schedule",
    "description": "Complete pre-production workflow for film project",
    "tasks": [
      {
        "id": "task_1",
        "name": "Script Development",
        "description": "Develop the complete screenplay",
        "title": "screenwriter",
        "needs": []
      }
    ]
  }
}
```

---

## Valid Crew Titles

When assigning tasks, use only these valid crew titles:
- `producer` - Producer (production management, scheduling, budgeting)
- `director` - Director (creative vision, casting, location scouting)
- `screenwriter` - Screenwriter (script development, dialogue)
- `cinematographer` - Cinematographer (visual style, camera work)
- `editor` - Editor (post-production, pacing, narrative flow)
- `sound_designer` - Sound Designer (audio, music, sound effects)
- `vfx_supervisor` - VFX Supervisor (visual effects, CGI)
- `storyboard_artist` - Storyboard Artist (visual planning, shot lists)

---

## Task Dependencies

Use the `needs` field to specify dependencies. For example:
```json
{
  "id": "task_2",
  "name": "Location Scouting",
  "title": "director",
  "needs": ["task_1"]
}
```
This means task_2 cannot start until task_1 is complete.

---

## Plan Naming

Choose clear, descriptive plan titles such as:
- "Pre-Production Schedule"
- "Principal Photography Plan"
- "Post-Production Workflow"
- "Full Film Production Pipeline"

---

## Complete Example

Here's a complete example of a pre-production plan:

```json
{
  "operation": "create",
  "title": "Pre-Production Schedule",
  "description": "Complete pre-production workflow from script development to pre-shoot preparation",
  "tasks": [
    {
      "id": "task_1",
      "name": "Script Development",
      "description": "Develop the complete screenplay with dialogue and scene descriptions",
      "title": "screenwriter",
      "needs": []
    },
    {
      "id": "task_2",
      "name": "Storyboard Creation",
      "description": "Create visual storyboards based on the finalized script",
      "title": "storyboard_artist",
      "needs": ["task_1"]
    },
    {
      "id": "task_3",
      "name": "Location Scouting",
      "description": "Find and secure filming locations matching scene requirements",
      "title": "director",
      "needs": ["task_1"]
    },
    {
      "id": "task_4",
      "name": "Casting",
      "description": "Hold auditions and select cast members for all roles",
      "title": "director",
      "needs": ["task_1"]
    },
    {
      "id": "task_5",
      "name": "Production Budget",
      "description": "Create detailed budget covering all production expenses",
      "title": "producer",
      "needs": ["task_1"]
    },
    {
      "id": "task_6",
      "name": "Shooting Schedule",
      "description": "Create detailed shooting schedule based on location and cast availability",
      "title": "producer",
      "needs": ["task_2", "task_3", "task_4", "task_5"]
    }
  ]
}
```

---

## Remember

1. **CHECK FIRST** if crew member info is already provided in input
2. Only call `crew_member` list operation if info is NOT provided
3. Analyze and plan tasks based on crew capabilities
4. **MUST** finish with `plan` create operation
5. Only provide final summary AFTER the plan is successfully created