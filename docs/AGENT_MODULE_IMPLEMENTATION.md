# Filmeto Agent Module Implementation

## Overview

The Filmeto Agent module provides a comprehensive AI agent system with LangGraph integration, streaming conversation interface, and tool calling capabilities. This document describes the architecture, components, and usage of the agent system.

## Architecture

### Core Components

```
agent/
├── __init__.py              # Module exports
├── filmeto_agent.py         # Main agent class with streaming interface
├── nodes.py                 # LangGraph nodes (coordinator, planner, executor, responder)
└── tools.py                 # Tool registry and built-in tools

agent/chat/
├── agent_chat_message.py    # Message classes (AgentMessage)
├── agent_chat_types.py      # Message and content types
├── agent_chat_signals.py    # Signal system for agent communication
└── content/                 # Structured content types

app/ui/panels/agent/
├── agent_panel.py           # UI panel with streaming integration
├── chat_history_widget.py   # Chat display with streaming support
└── prompt_input_widget.py   # User input component
```

## Key Features

### 1. LangGraph Integration

The agent uses LangGraph to implement a sophisticated workflow with multiple specialized nodes:

#### Node Types

- **Coordinator Node**: Analyzes user requests and decides the next action
  - Routes to tools, planner, or direct response
  - Manages conversation flow
  - Handles tool calling decisions

- **Planner Node**: Creates execution plans for complex tasks
  - Breaks down multi-step requests
  - Identifies required tools
  - Manages dependencies

- **Executor Node**: Executes tool calls
  - Runs tools with proper parameters
  - Handles tool results
  - Manages errors

- **Response Node**: Generates user-friendly responses
  - Synthesizes information from tools
  - Formats responses with markdown
  - Provides actionable suggestions

#### Workflow Graph

```
User Input → Coordinator → [Tools / Planner / Direct Response]
                ↑              ↓
                └──────────────┘
                   (feedback loop)
```

### 2. Tool System

The agent includes a comprehensive tool registry with built-in tools:

#### Built-in Tools

1. **Project Information**
   - `get_project_info`: Get current project details
   - `get_timeline_info`: Get timeline state

2. **Character Management**
   - `list_characters`: List all characters
   - `get_character_info`: Get character details

3. **Resource Management**
   - `list_resources`: List project resources (images, videos, audio)

4. **Task Management**
   - `create_task`: Create and submit AI generation tasks

#### Tool Registry

```python
from agent.tools import ToolRegistry, FilmetoBaseTool

# Create registry
registry = ToolRegistry(workspace=workspace, project=project)

# Get all tools
tools = registry.get_all_tools()

# Register custom tool
class CustomTool(FilmetoBaseTool):
    name = "custom_tool"
    description = "Custom tool description"
    # ... implementation

registry.register_tool(CustomTool(workspace=workspace, project=project))
```

### 3. Streaming Interface

The agent provides a streaming chat interface for real-time responses:

#### Streaming API

```python
from agent import FilmetoAgent

# Initialize agent
agent = FilmetoAgent(
    workspace=workspace,
    project=project,
    api_key="your-api-key",
    model="gpt-4o-mini",
    streaming=True
)

# Stream response
async for token in agent.chat_stream(
    message="Hello, agent!",
    on_token=lambda t: print(t, end=''),
    on_complete=lambda r: print("\nComplete!")
):
    # Process token
    pass

# Or get complete response
response = await agent.chat("Hello, agent!")
```

### 5. UI Integration

The `AgentPanel` provides a complete UI for agent interactions:

#### Features

- **Real-time streaming**: Messages appear token-by-token
- **Chat history**: Persistent conversation display
- **Input widget**: Multi-line input with auto-resize
- **Error handling**: Graceful error display

#### Usage

```python
from app.ui.panels.agent.agent_panel import AgentPanel

# Create panel
panel = AgentPanel(workspace=workspace)

# Panel automatically initializes agent when activated
# User can type messages and see streaming responses
```

## Configuration

### LLM Configuration

Configure the agent's LLM settings:

```python
agent = FilmetoAgent(
    workspace=workspace,
    project=project,
    api_key="your-openai-api-key",  # Optional, uses env var if not provided
    model="gpt-4o-mini",             # Model to use
    temperature=0.7,                 # Creativity level
    streaming=True                   # Enable streaming
)
```

### Settings Integration

The agent reads API keys from workspace settings:

```yaml
# workspace/settings.yml
openai_api_key: "sk-..."
```

## Usage Examples

### Example 1: Basic Chat

```python
agent = FilmetoAgent(workspace=workspace, project=project)

# Simple question
response = await agent.chat("What characters are in my project?")
print(response)
```

### Example 2: Complex Task

```python
# Multi-step request
response = await agent.chat(
    "List all characters, then create a text2img task using the first actor"
)
# Agent will:
# 1. Use list_characters tool
# 2. Use get_character_info tool
# 3. Use create_task tool
# 4. Provide summary
```

### Example 3: Streaming with Callbacks

```python
def on_token(token: str):
    print(token, end='', flush=True)

def on_complete(response: str):
    print("\n✅ Complete!")

async for token in agent.chat_stream(
    message="Tell me about my project",
    on_token=on_token,
    on_complete=on_complete
):
    pass
```

## Extending the Agent

### Adding Custom Tools

Create custom tools by extending `FilmetoBaseTool`:

```python
from agent.tools import FilmetoBaseTool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    param1: str = Field(description="Parameter description")

class MyCustomTool(FilmetoBaseTool):
    name: str = "my_tool"
    description: str = "Tool description for LLM"
    args_schema: type[BaseModel] = MyToolInput
    
    def _run(self, param1: str) -> str:
        """Tool implementation."""
        # Access workspace and project
        project = self.project
        workspace = self.workspace
        
        # Implement tool logic
        result = f"Processed: {param1}"
        return result

# Register tool
agent.tool_registry.register_tool(
    MyCustomTool(workspace=workspace, project=project)
)
```

### Adding Custom Nodes

Extend the graph with custom nodes:

```python
from agent.nodes import AgentState

class CustomNode:
    def __init__(self, llm):
        self.llm = llm
    
    def __call__(self, state: AgentState) -> AgentState:
        # Process state
        messages = state["messages"]
        
        # Custom logic
        response = self.llm.invoke(messages)
        
        return {
            "messages": [response],
            "next_action": "coordinator",
            "context": state.get("context", {}),
            "iteration_count": state.get("iteration_count", 0) + 1
        }

# Add to graph (requires modifying filmeto_agent.py)
```

## Error Handling

The agent includes comprehensive error handling:

```python
try:
    response = await agent.chat("Your message")
except Exception as e:
    print(f"Error: {e}")
    # Agent will display error in UI
```

## Performance Considerations

### Streaming Performance

- Tokens are emitted as they're generated
- Small delay (10ms) between tokens for smooth display
- No buffering delays

### Memory Management

- Messages are managed in-memory during sessions
- LangGraph uses memory checkpointing for agent state
- Message persistence can be implemented as needed

### API Rate Limits

- Agent respects OpenAI rate limits
- Implement retry logic if needed
- Consider using rate limiting middleware

## Testing

### Unit Tests

```python
import pytest
from agent import FilmetoAgent

@pytest.mark.asyncio
async def test_agent_chat():
    agent = FilmetoAgent(workspace=mock_workspace, project=mock_project)
    response = await agent.chat("Test message")
    assert response is not None
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_tool_execution():
    agent = FilmetoAgent(workspace=workspace, project=project)
    response = await agent.chat("List all characters")
    assert "characters" in response.lower()
```

## Troubleshooting

### Common Issues

1. **Agent not initialized**
   - Ensure project is loaded
   - Check workspace settings

2. **API key errors**
   - Set `openai_api_key` in settings
   - Or pass `api_key` parameter

3. **Streaming not working**
   - Ensure `streaming=True`
   - Check async event loop

4. **Tool errors**
   - Verify project context is set
   - Check tool implementation

## Future Enhancements

### Planned Features

1. **Multi-modal support**: Image and video understanding
2. **Memory persistence**: Long-term memory across sessions
3. **Custom prompts**: User-defined system prompts
4. **Tool marketplace**: Share and discover tools
5. **Agent analytics**: Track usage and performance
6. **Voice interface**: Speech-to-text integration
7. **Collaborative agents**: Multi-agent coordination

## Dependencies

```
langgraph==1.0.5
langchain>=1.0.0,<2.0.0
langchain-core>=1.0.0,<2.0.0
langchain-openai>=1.0.0,<2.0.0
```

## License

Part of the Filmeto project.

## Support

For issues and questions:
- Check documentation
- Review examples
- Open GitHub issue

