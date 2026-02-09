# Filmeto Agent System

The Filmeto Agent system provides AI-powered conversational capabilities for the Filmeto application. It implements a multi-agent architecture with streaming message capabilities, centered around a crew-based system with a producer orchestrating workflows.

## Architecture Overview

The agent system follows a crew-based architecture where:
- **Crew Members** are the core AI agents with specific roles, skills, and personalities
- **Producer** acts as the orchestrator, creating execution plans and delegating tasks
- **FilmetoAgent** serves as the central coordinator managing the entire system

## Core Components

### FilmetoAgent
The main orchestrator class that:
- Manages all crew members in the system
- Handles message routing and streaming
- Coordinates plan execution
- Maintains conversation history
- Provides the main interface for external systems

### CrewMember
Represents individual AI agents with:
- Configuration (name, description, model, temperature, etc.)
- Skills and capabilities
- Personality (soul) integration
- LLM interaction capabilities
- Conversation history management

### AgentMessage & ContentType
- Standardized message format used throughout the system
- Message type is determined from the structured_content (defaults to TEXT if empty)
- Supports multiple content types (text, code_block, thinking, tool_call, tool_response, progress, typing, metadata, error, image, video, audio, table, chart, link, button, form, file_attachment, plan, step, task_list, skill)
- Includes metadata, timestamps, and sender information

### StreamEvent
Handles real-time streaming events for UI integration, including:
- Agent thinking indicators
- LLM call start/end notifications
- Skill execution updates
- Plan updates
- Error events

## Crew-Based Workflow

### 1. Crew Member Registration
- Crew members are loaded from project configuration files
- Each crew member has a name, title (crew_title), description, skills, and personality (soul)
- Both names and titles are indexed for flexible referencing

### 2. Producer Orchestration
When a user sends a message:
- If a specific crew member is mentioned (e.g., `@director`, `@producer`), that member responds
- If no specific member is mentioned, the producer takes priority
- The producer creates execution plans with detailed tasks for crew members
- Tasks specify which crew member should handle them (by name or title)

### 3. Plan Execution
- Plans contain ordered tasks with dependencies
- Each task specifies a `title` (which can be a crew member's name or title)
- Tasks are executed when dependencies are satisfied
- Crew members execute tasks and update plan state as needed

## Key Features

### Flexible Agent Referencing
- Crew members can be referenced by either their specific name or role title
- Example: `@elena_vasquez` or `@producer` both work to reach the same agent
- Enhanced lookup system supports both naming conventions

### Detailed Producer Context
- Producer receives comprehensive information about all crew members
- Includes names, titles, and skill sets for informed decision-making
- Clear instructions that title can be either name or title

### Crew Member Sorting by Importance
- Crew members are automatically sorted by their importance in film production
- Order: Producer → Director → Screenwriter → Cinematographer → Editor → Sound Designer → VFX Supervisor → Storyboard Artist
- This ensures the most critical roles appear first when listing crew members
- The `CrewTitle` enum in `crew_title.py` defines the importance hierarchy

### Streaming Architecture
- Real-time message streaming with event callbacks
- Support for UI integration with streaming events
- Asynchronous processing throughout the system

### Skill Integration
- Crew members can execute specific skills/tools
- Skills are configured per crew member
- Skill execution is tracked and reported through streaming events

### Plan Management
- Dynamic plan creation and execution
- Task dependencies and readiness checking
- Plan updates during execution
- State management for ongoing workflows

## Usage Patterns

### Basic Interaction
```python
from agent.filmeto_agent import FilmetoAgent

# Initialize the agent system with a project
agent = FilmetoAgent(project=your_project)

# Stream responses to a message
async for response in agent.chat_stream("Create a video project"):
    print(response)
```

### Crew Member Mentioning
```
"Hey @director, what do you think about this scene?"
"Can you @producer create a plan for this project?"
```

### Plan Creation Flow
1. User sends request to producer (either directly or implicitly)
2. Producer analyzes request and crew capabilities
3. Producer creates execution plan with specific tasks
4. Tasks are assigned to appropriate crew members
5. Crew members execute tasks and report back
6. Plan is updated dynamically as work progresses

## System Integration

### UI Integration
- Stream events enable real-time UI updates
- Different message types render as appropriate UI components
- Agent status indicators (thinking, processing, etc.)

### Project Context
- Crew members are loaded per project
- Project-specific configurations and skills
- Isolated agent contexts per project

### LLM Service Integration
- Configurable LLM providers and models
- Per-member model and temperature settings
- Error handling and fallback mechanisms

## Configuration

Crew members are defined in markdown files with frontmatter configuration:

```markdown
---
name: producer
description: Owns budget, schedule, and delivery risks.
soul: elena_vasquez_soul
skills: [planning, coordination]
model: gpt-4o-mini
temperature: 0.3
max_steps: 5
color: "#7b68ee"
icon: "💼"
---
You are the Producer. Focus on feasibility, staffing, budgets, and production logistics.
```

## Error Handling

- Graceful degradation when LLM services are unavailable
- Detailed error reporting through message system
- Plan execution continues with error handling
- Fallback mechanisms for missing crew members

## Extensibility

- New crew members can be added by creating configuration files
- Skills can be extended per crew member
- Custom souls (personalities) can be defined
- Model and behavior parameters are configurable per member