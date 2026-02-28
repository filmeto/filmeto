---
name: production_plan
description: Creates a comprehensive film production plan by analyzing crew capabilities, breaking down tasks, and scheduling crew member assignments. When invoking this skill, you MUST include complete team member information (name, role, description, and skills for each member) in the prompt to enable direct task assignment without additional queries.
tools:
  - speak_to
  - plan
---
# Film Production Plan Creation

## CRITICAL: Route First, Plan Only When Needed

**IMPORTANT**: Before creating any plan, you MUST first evaluate whether the task can be handled by a SINGLE crew member. Many tasks don't need complex planning - they just need direct routing.

### Decision Flow:
1. **Can ONE crew member handle this?** → Use `speak_to` tool with `specify` mode
2. **Does it need MULTIPLE crew members collaborating?** → Create a plan with `plan` tool

---

## Step 0: CRITICAL - Evaluate Task Complexity (MUST DO FIRST)

**Before any other step**, analyze the user's request:

### Single Crew Member Tasks (Use `speak_to` → specify mode)

Examples of tasks that ONE person can handle:
- "Write a scene description" → @screenwriter
- "Create a storyboard for scene 5" → @storyboard_artist
- "Design the lighting for the opening shot" → @cinematographer
- "Edit this sequence" → @editor
- "Add sound effects to this clip" → @sound_designer
- "Review the script" → @director
- "Create a shot list" → @director
- Any task with clear single ownership

**If task can be handled by ONE crew member:**

```json
{
  "type": "tool",
  "tool_name": "speak_to",
  "tool_args": {
    "mode": "specify",
    "target": "screenwriter",
    "message": "Please write a scene description for the opening sequence."
  }
}
```

**DO NOT create a plan for single-person tasks. Stop here and respond.**

### Multi-Crew Member Tasks (Use `plan` tool)

Examples of tasks requiring COLLABORATION:
- "Produce a complete short film" → Needs screenwriter → director → cinematographer → editor
- "Create a full video from script to final cut" → Multiple stages
- "Develop and shoot a commercial" → Coordination needed
- "Plan the entire pre-production workflow" → Dependencies between tasks
- Any task where output of one person is input for another

**Only proceed to Step 1-3 if task genuinely needs multiple crew members working together with dependencies.**

---

## Step 1: Verify Team Member Information (Only for Multi-Crew Tasks)

Check if the prompt contains team member information.

**If prompt contains team member information**: Use this information directly for task assignment.

**If prompt is missing team member information**: Use default generic roles for task assignment:
- `producer` - Producer
- `director` - Director
- `screenwriter` - Screenwriter
- `cinematographer` - Cinematographer
- `editor` - Editor
- `sound_designer` - Sound Designer
- `vfx_supervisor` - VFX Supervisor
- `storyboard_artist` - Storyboard Artist

---

## Step 2: Analyze and Break Down the Task (Only for Multi-Crew Tasks)

Analyze the user's production requirements:
- Decompose the overall production goal into specific, actionable tasks
- Identify task dependencies (which tasks must complete before others can start)
- Match each task to the most appropriate team member based on their role and skills

---

## Step 3: Create and Store the Production Plan (Only for Multi-Crew Tasks)

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

## Complete Examples

### Example 1: Single Crew Member Task (COMMON)

**User request**: "Create a storyboard for scene 5"

**Analysis**: This is a single task that the storyboard artist can handle alone.

**Action**: Use `speak_to` tool (DO NOT create a plan)

```json
{
  "type": "tool",
  "tool_name": "speak_to",
  "tool_args": {
    "mode": "specify",
    "target": "storyboard_artist",
    "message": "Please create a storyboard for scene 5 based on the script."
  }
}
```

### Example 2: Multi-Crew Member Task

**User request**: "Produce a complete short film from concept to final cut"

**Analysis**: This requires multiple crew members working in sequence with dependencies.

**Action**: Create a plan

```json
{
  "type": "tool",
  "tool_name": "plan",
  "tool_args": {
    "operation": "create",
    "title": "Short Film Production Pipeline",
    "description": "Complete workflow from concept to final delivery",
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
        "name": "Shot Planning",
        "description": "Plan camera shots and visual approach",
        "title": "director",
        "needs": ["task_2"]
      },
      {
        "id": "task_4",
        "name": "Principal Photography",
        "description": "Execute the planned shots",
        "title": "cinematographer",
        "needs": ["task_3"]
      },
      {
        "id": "task_5",
        "name": "Post-Production Editing",
        "description": "Edit footage into final cut",
        "title": "editor",
        "needs": ["task_4"]
      }
    ]
  }
}
```

---

## Remember

1. **EVALUATE FIRST** - Can one crew member handle this?
2. **Single task?** → Use `speak_to` with `specify` mode,3. **Multiple tasks with dependencies?** → Use `plan` tool
4. Only create plans when genuinely needed
5. Most user requests can be handled by routing to a single crew member
