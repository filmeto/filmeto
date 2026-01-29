# AgentChatWidget Delayed Project Switching - Implementation Summary

## Overview

Implemented **delayed project switching** in `AgentChatWidget` to ensure that FilmetoAgent instances always correspond to the workspace's **real** current project, preventing stale references and incorrect agent instances.

## Problem Statement

### Original Issue

When `on_project_switch()` was called, it would immediately create a new agent instance based on the project parameter passed to it. However, this created a problem:

1. `on_project_switch()` might be called with project "B"
2. Agent instance for project "B" is created immediately
3. But the workspace might still be on project "A"
4. Or the workspace might switch to project "C" instead
5. Result: Agent instance doesn't match the workspace's actual state

### The Solution: Delayed Switching

Instead of immediately switching the agent instance:
1. Store the **target** project when `on_project_switch()` is called
2. Set a flag indicating sync is needed
3. When the agent is actually needed (e.g., before sending a message), call `sync_agent_instance()`
4. `sync_agent_instance()` queries `workspace.get_project()` to get the **real** current project
5. Create/switch agent instance to match the workspace's real project

## Implementation Details

### New Instance Variables

```python
# Target project for delayed switching
self._target_project_name = None
self._target_project = None
self._agent_needs_sync = False
```

### Modified Methods

#### `on_project_switch(project)` - Now Delayed

**Before:**
```python
def on_project_switch(self, project):
    # Immediately switch agent instance
    self.agent = FilmetoAgent.get_instance(...)
    self._current_project_name = new_project_name
```

**After:**
```python
def on_project_switch(self, project):
    # Store target and mark sync needed
    self._target_project_name = new_project_name
    self._agent_needs_sync = True
    # Update UI immediately
    # DON'T switch agent yet
```

#### New: `sync_agent_instance()` - Performs Actual Switch

```python
def sync_agent_instance(self):
    if not self._agent_needs_sync:
        return

    # Get REAL current project from workspace
    current_workspace_project = self.workspace.get_project()
    real_project_name = extract_project_name(current_workspace_project)

    # Switch agent to real project
    self.agent = FilmetoAgent.get_instance(
        workspace=self.workspace,
        project_name=real_project_name,  # Use real project, not target
        ...
    )

    self._current_project_name = real_project_name
    self._agent_needs_sync = False
```

#### `_process_message_async(message)` - Auto-sync Before Use

```python
async def _process_message_async(self, message: str):
    # First, sync agent if needed
    self.sync_agent_instance()

    # Then use the agent
    await self.agent.chat(message)
```

### New Query Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_current_project_name()` | `str` | Agent instance's current project |
| `get_target_project_name()` | `str` | Target project (if switch pending) |
| `get_workspace_current_project_name()` | `str` | Workspace's real current project |
| `is_agent_sync_needed()` | `bool` | Whether sync is pending |

## Flow Diagram

```
User requests project switch
         │
         ▼
┌─────────────────────────────────┐
│ on_project_switch("project_b")   │
│  - Store target = "project_b"    │
│  - Set _agent_needs_sync = True  │
│  - Update UI (history, plan)     │
│  - DON'T touch agent             │
└─────────────────────────────────┘
         │
         ▼
Time passes...
Workspace may or may not switch
         │
         ▼
User sends message
         │
         ▼
┌─────────────────────────────────┐
│ _process_message_async()         │
│  - Calls sync_agent_instance()   │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│ sync_agent_instance()            │
│  - Gets workspace.get_project()  │
│  - Extracts REAL project name   │
│  - Switches agent to real project│
│  - Clears _agent_needs_sync      │
└─────────────────────────────────┘
         │
         ▼
Message sent to correct agent
```

## Testing

Created comprehensive tests in `tests/test_agent_chat_delayed_switch.py`:

1. **Delayed Switching Test**
   - Verifies agent is not switched immediately
   - Verifies sync uses workspace's real project
   - Verifies correct instance is created

2. **Stale Reference Prevention Test**
   - Requests switch to project Y
   - Workspace switches to project Z instead
   - Sync creates agent for project Z (real project)
   - No agent created for project Y (stale target)

### Test Results

```
============================================================
Testing Delayed Project Switching
============================================================

✓ Agent NOT switched immediately after on_project_switch()
✓ Agent switched to workspace's REAL current project on sync
✓ Correctly synced to real project, not stored target
✓ No instance created for stale target project

============================================================
Testing Stale Reference Prevention
============================================================

✓ Used workspace's real project, not stale target
✓ No instance created for stale target project

ALL TESTS PASSED! ✓✓✓
```

## Benefits

1. **Prevents Stale References**: Agent always matches workspace's real state
2. **Flexible Timing**: UI updates immediately, agent updates when needed
3. **Correct Instances**: Only creates agent instances for projects that actually exist
4. **Automatic Sync**: No manual intervention needed in most cases
5. **Debugging Support**: Multiple query methods to inspect sync state

## Migration Guide

### For Existing Code

The changes are backward compatible. Existing code using `on_project_switch()` will continue to work:

```python
# This still works exactly the same
chat_widget.on_project_switch(new_project)
```

The only difference is that the agent instance now switches lazily and uses the workspace's real current project.

### New Optional Features

```python
# Check if sync is needed
if chat_widget.is_agent_sync_needed():
    print(f"Pending switch: {chat_widget.get_target_project_name()}")

# Force immediate sync (rarely needed)
chat_widget.sync_agent_instance()

# Query workspace's real project
real_project = chat_widget.get_workspace_current_project_name()
```

## Files Modified

1. `app/ui/chat/agent_chat.py`
   - Added delayed switching logic
   - Added `sync_agent_instance()` method
   - Modified `on_project_switch()` to be delayed
   - Modified `_process_message_async()` to auto-sync
   - Added new query methods

2. `tests/test_agent_chat_delayed_switch.py` (new)
   - Comprehensive tests for delayed switching
   - Tests for stale reference prevention

3. `docs/AGENT_CHAT_PROJECT_SWITCHING.md`
   - Updated to explain delayed switching
   - Added "Why Delayed Switching?" section
   - Updated API reference

## Key Insight

The fundamental insight is:

> **Don't trust the project parameter passed to `on_project_switch()` - always query `workspace.get_project()` when creating the agent instance.**

This ensures the agent always corresponds to the workspace's true state, regardless of when or how the project switch was requested.
