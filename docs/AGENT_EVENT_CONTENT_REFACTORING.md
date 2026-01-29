# Agent Event & Content Architecture Refactoring

## Overview

Major refactoring of the agent event system to improve structure, tracking, and maintainability.

## Changes Summary

### 1. StructureContent Subclass Hierarchy

**File**: `agent/chat/structure_content.py`

Created a comprehensive subclass hierarchy for StructureContent with specific schemas for each content type:

#### Base Class
- **StructureContent**: Base class with common fields
  - `content_id`: Unique ID for tracking
  - `status`: ContentStatus (CREATING, UPDATING, COMPLETED, FAILED)
  - `parent_id`: For hierarchical content relationships
  - Methods: `update()`, `complete()`, `fail()`

#### Subclasses
1. **TextContent**: Plain text messages
2. **ThinkingContent**: Agent thinking process with step tracking
3. **ToolCallContent**: Tool invocation details (tool_name, tool_input, tool_status)
4. **ToolResponseContent**: Tool execution results (result, error, tool_status)
5. **ProgressContent**: Progress updates (with parent_id for linking to tool)
6. **CodeBlockContent**: Code with syntax highlighting
7. **ImageContent**: Image references
8. **VideoContent**: Video references
9. **MetadataContent**: Metadata updates (todo, task status)
10. **ErrorContent**: Error messages with details
11. **FileAttachmentContent**: File attachments

#### Factory Function
```python
def create_content(content_type: ContentType, **kwargs) -> StructureContent
```

### 2. AgentEvent Enhancement

**File**: `agent/event/agent_event.py`

Added `content` field to AgentEvent:
```python
@dataclass
class AgentEvent:
    event_type: str
    project_name: str
    react_type: str
    run_id: str
    step_id: int
    sender_id: str = ""
    sender_name: str = ""
    content: Optional['StructureContent'] = None  # NEW
    payload: Dict[str, Any] = field(default_factory=dict)  # Legacy, deprecated
```

All factory methods updated to support `content` parameter:
- `AgentEvent.create(content=...)`
- `AgentEvent.error(content=...)`
- `AgentEvent.final(content=...)`
- `AgentEvent.tool_start(content=...)`
- `AgentEvent.tool_progress(content=...)`
- `AgentEvent.tool_end(content=...)`

### 3. CrewMember Simplification

**File**: `agent/crew/crew_member.py`

**Removed**: Direct AgentMessage creation and sending
- Removed `StructureContent` creation for LLM_THINKING
- Removed `AgentMessage` creation
- Removed `await self.signals.send_agent_message(msg)`

**Now**: Only returns AgentEvent
- Enhances events with sender information
- Forwards all events to FilmetoAgent
- FilmetoAgent handles event→message conversion

### 4. FilmetoAgent Central Conversion

**File**: `agent/filmeto_agent.py`

#### New Method: `_convert_event_to_message()`

Central event-to-message conversion with:
- Support for event.content (StructureContent subclasses)
- Legacy fallback for event.payload
- Automatic message type mapping
- Content lifecycle management

#### Enhanced Method: `_stream_crew_member()`

Features:
1. **Content Tracking**: Tracks content IDs for hierarchical relationships
   ```python
   content_tracking: Dict[str, str] = {}  # tool_name → content_id
   ```

2. **Hierarchical Content**:
   - TOOL_START: Creates ToolCallContent with content_id
   - TOOL_PROGRESS: Creates ProgressContent with parent_id
   - TOOL_END: Creates ToolResponseContent, marks completed

3. **Status Management**:
   - New content: status=ContentStatus.CREATING
   - Updated content: status=ContentStatus.UPDATING
   - Completed content: status=ContentStatus.COMPLETED
   - Failed content: status=ContentStatus.FAILED

## Event Flow

### Before Refactoring
```
React.chat_stream
    → CrewMember.chat_stream
    → Creates AgentMessage directly
    → Sends via signals
    → UI
```

### After Refactoring
```
React.chat_stream
    → CrewMember.chat_stream
    → Returns AgentEvent (with sender_id/sender_name)
    → FilmetoAgent._stream_crew_member
    → Creates StructureContent subclasses
    → _convert_event_to_message()
    → Sends via signals
    → UI
```

## Content Lifecycle Example

### Tool Execution Flow

1. **TOOL_START Event**:
   ```python
   tool_content = ToolCallContent(
       tool_name='execute_skill',
       tool_input={'skill_name': 'writer'},
       title='Tool: execute_skill'
   )
   # status: CREATING
   # content_id: abc-123
   ```

2. **TOOL_PROGRESS Event**:
   ```python
   progress_content = ProgressContent(
       progress='Executing skill...',
       parent_id='abc-123'  # Links to tool call
   )
   # status: UPDATING
   ```

3. **TOOL_END Event**:
   ```python
   response_content = ToolResponseContent(
       tool_name='execute_skill',
       result='Done!',
       parent_id='abc-123'
   )
   response_content.complete()
   # status: COMPLETED
   ```

## Hierarchical Tracking

UI can track related content via `parent_id`:
```
ToolCall (abc-123)
    ├── ProgressContent (def-456, parent_id=abc-123)
    ├── ProgressContent (ghi-789, parent_id=abc-123)
    └── ToolResponseContent (jkl-012, parent_id=abc-123)
```

## Backward Compatibility

### Legacy Payload Support
- Event `payload` field still available
- `_convert_event_to_message()` handles both:
  - New: `event.content` (StructureContent subclass)
  - Legacy: `event.payload` (dict)

### Existing Code
- All existing AgentEvent.create() calls still work
- Payload-only events automatically converted to appropriate content

## Benefits

1. **Type Safety**: Specific content types with defined schemas
2. **Tracking**: Content ID enables lifecycle tracking
3. **Hierarchy**: parent_id enables related content grouping
4. **Centralization**: Single conversion point (FilmetoAgent)
5. **Maintainability**: Clear separation of concerns
6. **Debugging**: Content status and IDs for tracing

## Migration Guide

### For Event Creation

**Old Way**:
```python
event = AgentEvent.create(
    event_type='tool_start',
    tool_name='my_tool',
    input={'arg': 'value'}
)
```

**New Way** (Recommended):
```python
from agent.chat.structure_content import ToolCallContent

event = AgentEvent.create(
    event_type='tool_start',
    content=ToolCallContent(
        tool_name='my_tool',
        tool_input={'arg': 'value'},
        title='Tool: my_tool'
    )
)
```

### For Message Handling

**No Changes Required**: UI components still receive AgentMessage with structured_content list.

## Testing

Run tests to verify:
```bash
python -c "
from agent.chat.structure_content import ToolCallContent, ContentStatus
content = ToolCallContent(tool_name='test', tool_input={})
content.complete()
print(f'Status: {content.status}')  # COMPLETED
"
```
