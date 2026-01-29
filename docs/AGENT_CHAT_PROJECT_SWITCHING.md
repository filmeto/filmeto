# AgentChatWidget Project Switching Guide

## Overview

`AgentChatWidget` supports seamless project switching with **delayed agent instance switching**. Each project gets its own `FilmetoAgent` instance that persists across switches, enabling efficient multi-project workflows while ensuring the agent always matches the workspace's real current project.

## Key Features

- **Static Instance Management**: Agent instances are cached and reused across the application
- **Project Isolation**: Each project has its own agent instance with separate conversation history
- **Delayed Switching**: Agent instances switch only when needed (lazy switching), preventing stale references
- **Workspace Sync**: Agent sync uses the workspace's real current project, not stored references
- **Instance Tracking**: Query current, target, and workspace project information

## Why Delayed Switching?

### The Problem

When a project switch is requested, the workspace might not have actually switched yet. If we immediately create a new agent instance based on the requested project, we might create an instance for the wrong project.

### The Solution

**Delayed switching with workspace sync:**
1. `on_project_switch()` stores the target project but doesn't switch the agent yet
2. When the agent is needed (e.g., before sending a message), `sync_agent_instance()` is called
3. `sync_agent_instance()` queries the workspace's **real** current project
4. Agent instance is created/switched to match the workspace's actual state

This ensures the agent always corresponds to the workspace's true current project, not a stale or outdated reference.

## Basic Usage

### Initializing AgentChatWidget

```python
from app.ui.chat.agent_chat import AgentChatWidget
from app.data.workspace import Workspace

# Create workspace and widget
workspace = Workspace("/path/to/workspace", "project_name")
chat_widget = AgentChatWidget(workspace)

# Agent will be lazily initialized on first message
```

### Switching Projects

```python
# Request project switch (delayed - agent not switched yet)
chat_widget.on_project_switch("new_project")

# Agent will sync when needed (e.g., before sending message)
# The sync will use workspace's REAL current project at that time
```

### Manual Sync (Optional)

In most cases, you don't need to manually sync. The widget automatically syncs before sending messages. However, you can manually trigger a sync if needed:

```python
# Force immediate agent sync
chat_widget.sync_agent_instance()
```

### Querying Current State

```python
# Get the agent instance's current project
current = chat_widget.get_current_project_name()

# Get the target project (if a switch is pending)
target = chat_widget.get_target_project_name()

# Get the workspace's real current project
workspace_project = chat_widget.get_workspace_current_project_name()

# Check if sync is needed
needs_sync = chat_widget.is_agent_sync_needed()

# Get agent instance key
instance_key = chat_widget.get_agent_instance_key()
# Returns: "workspace_path:project_name"
```

## How It Works

### Delayed Switch Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. on_project_switch(project)                               │
│    - Store target project name                             │
│    - Set _agent_needs_sync = True                          │
│    - Update UI immediately                                 │
│    - DON'T switch agent yet                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Time passes... workspace switches projects                │
│    - Widget doesn't know yet                                │
│    - Target is stored but not acted upon                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. sync_agent_instance() (called before using agent)         │
│    - Get workspace's REAL current project                   │
│    - Compare with current agent instance                    │
│    - Switch agent to match workspace's real project         │
│    - Clear _agent_needs_sync flag                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Point: Workspace Real Project

The critical difference is **where** we get the project name:

| Approach | Project Source | Problem |
|----------|---------------|---------|
| Immediate switching | Parameter passed to `on_project_switch()` | May be stale if workspace hasn't switched yet |
| **Delayed switching** | `workspace.get_project()` when syncing | Always gets the real current project |

## Instance Key Format

Each agent instance is identified by a unique key:

```
workspace_path:project_name
```

For example:
```
/Users/username/filmeto_workspace:my_video_project
```

### Project Switch Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User switches project                                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ on_project_switch(project)                                   │
│  1. Extract project name                                    │
│  2. Check if different from current                         │
│  3. Update tracking variables                               │
│  4. Get/create agent instance via FilmetoAgent.get_instance │
│  5. Refresh UI components                                   │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ FilmetoAgent.get_instance()                                  │
│  1. Generate instance key                                   │
│  2. Check if instance exists in cache                       │
│  3. Return existing instance OR create new one              │
└─────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ UI Updates                                                   │
│  - Reload conversation history                              │
│  - Refresh plan widget                                      │
│  - Update agent reference                                   │
└─────────────────────────────────────────────────────────────┘
```

### Instance Lifecycle

```
Workspace: /ws1
├── project_a → Agent Instance A (created once, reused)
├── project_b → Agent Instance B (created once, reused)
└── project_c → Agent Instance C (created once, reused)

When switching: project_a → project_b → project_a
- Instance A is created on first switch to project_a
- Instance B is created on switch to project_b
- Switch back to project_a reuses Instance A
```

## Advanced Usage

### Multiple Widgets with Same Workspace

```python
# Multiple widgets share agent instances for the same project
widget1 = AgentChatWidget(workspace)
widget2 = AgentChatWidget(workspace)

# Both widgets pointing to same project
widget1.on_project_switch("project_x")
widget2.on_project_switch("project_x")

# They share the same agent instance
assert widget1.agent is widget2.agent  # True
```

### Checking Active Instances

```python
from agent.filmeto_agent import FilmetoAgent

# List all active agent instances
instances = FilmetoAgent.list_instances()
# Returns: ['/ws1:project_a', '/ws1:project_b', ...]

# Check if specific instance exists
exists = FilmetoAgent.has_instance(workspace, "project_a")

# Remove specific instance
removed = FilmetoAgent.remove_instance(workspace, "project_a")

# Clear all instances
FilmetoAgent.clear_all_instances()
```

### Integration with Workspace Events

```python
class MyApplication:
    def __init__(self):
        self.workspace = Workspace("/path", "default")
        self.chat_widget = AgentChatWidget(self.workspace)

        # Connect to project change signal
        self.workspace.project_changed.connect(self._on_project_changed)

    def _on_project_changed(self, new_project):
        """Handle workspace project change event."""
        self.chat_widget.on_project_switch(new_project)
        print(f"Switched to: {self.chat_widget.get_current_project_name()}")
```

## Best Practices

### 1. Always Use on_project_switch()

```python
# ✓ Good - Proper instance management
chat_widget.on_project_switch(new_project)

# ✗ Bad - Bypasses instance tracking
chat_widget.agent = FilmetoAgent(workspace, new_project)
```

### 2. Check Project Before Switching

```python
current = chat_widget.get_current_project_name()
if current != new_project_name:
    chat_widget.on_project_switch(new_project_name)
```

### 3. Handle Null Projects

```python
# on_project_switch handles None gracefully
# It will use "default" as the project name
chat_widget.on_project_switch(None)  # OK
```

### 4. Thread Safety

The instance management is designed for single-threaded Qt event loop usage.
For multi-threaded scenarios, add proper locking:

```python
import threading

class ThreadSafeAgentChatWidget(AgentChatWidget):
    def __init__(self, workspace, parent=None):
        super().__init__(workspace, parent)
        self._lock = threading.Lock()

    def on_project_switch(self, project):
        with self._lock:
            super().on_project_switch(project)
```

## Troubleshooting

### Issue: Wrong agent instance after project switch

**Solution**: Ensure you're calling `on_project_switch()` and not directly setting `self.agent`.

```python
# ✓ Correct
chat_widget.on_project_switch(new_project)

# ✗ Wrong
chat_widget.agent = some_agent
```

### Issue: Conversation history doesn't update

**Solution**: The `on_project_switch()` method automatically triggers history reload.
If it's not working, check that `chat_history_widget._load_recent_conversation()` is implemented.

### Issue: Old agent messages appearing after switch

**Solution**: This is expected behavior if both projects are active. Each agent instance
maintains its own conversation history independently.

## API Reference

### AgentChatWidget Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `on_project_switch(project)` | `None` | Switch to a new project |
| `update_project(project)` | `None` | Legacy method, delegates to `on_project_switch` |
| `get_current_project_name()` | `str \| None` | Get current project name |
| `get_current_project()` | `Any \| None` | Get current project object |
| `get_agent_instance_key()` | `str \| None` | Get agent instance key |

### FilmetoAgent Static Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_instance(workspace, project_name, ...)` | `FilmetoAgent` | Get or create agent instance |
| `has_instance(workspace, project_name)` | `bool` | Check if instance exists |
| `remove_instance(workspace, project_name)` | `bool` | Remove specific instance |
| `list_instances()` | `List[str]` | List all instance keys |
| `clear_all_instances()` | `None` | Remove all instances |

## Example: Complete Workflow

```python
from app.ui.chat.agent_chat import AgentChatWidget
from app.data.workspace import Workspace
from agent.filmeto_agent import FilmetoAgent

class FilmetoApp:
    def __init__(self):
        # Setup workspace
        self.workspace = Workspace("/path/to/workspace")
        self.chat_widget = AgentChatWidget(self.workspace)

        # Start with default project
        initial_project = self.workspace.get_project()
        if initial_project:
            self.chat_widget.on_project_switch(initial_project)

    def switch_to_project(self, project_name: str):
        """Switch to a different project."""
        project = self.workspace.get_project(project_name)
        self.chat_widget.on_project_switch(project)

        # Verify switch
        current = self.chat_widget.get_current_project_name()
        print(f"Now on project: {current}")
        print(f"Agent instance: {self.chat_widget.get_agent_instance_key()}")
        print(f"Active instances: {FilmetoAgent.list_instances()}")

    def send_message(self, message: str):
        """Send a message to the current project's agent."""
        # Message is handled by the current project's agent
        asyncio.create_task(self.chat_widget._process_message_async(message))
```

## Testing

Run the project switching tests:

```bash
python tests/test_agent_chat_project_switch.py
```

Expected output:
```
=== Project Switching Test ===

1. Switch to project_a:
Switching from None to project_a
Current instance key: /tmp/test_ws:project_a
All instances: ['/tmp/test_ws:project_a']

2. Switch to project_b:
Switching from project_a to project_b
Current instance key: /tmp/test_ws:project_b
All instances: ['/tmp/test_ws:project_a', '/tmp/test_ws:project_b']

3. Switch back to project_a:
Switching from project_b to project_a
Current instance key: /tmp/test_ws:project_a
All instances: ['/tmp/test_ws:project_a', '/tmp/test_ws:project_b']

4. Verify instance reuse:
   agent_a1 is agent_a2: True
   agent_a1 is agent_b: False
   Total instances: 2

ALL TESTS PASSED! ✓✓✓
```
