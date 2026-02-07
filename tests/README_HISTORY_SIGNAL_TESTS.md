# AgentChatWidget History & Signal Tests

## Overview

This test suite verifies that `AgentChatListWidget` correctly:
1. Loads existing historical messages from `message.log`
2. Groups messages with the same `message_id` (multi-part messages)
3. Auto-loads new messages via the polling mechanism
4. Handles signal-based message delivery

## Test Files

### 1. `test_agent_chat_history_signals_cli.py` - CLI Test Suite

A command-line test that runs automatically and verifies:
- **History Loading**: Loads messages from `message.log` and displays statistics
- **Signal Saving**: Sends test messages via `AgentChatSignals` and verifies they're saved
- **Message Grouping**: Verifies messages with the same `message_id` are grouped correctly

**Run:**
```bash
cd /Users/classfoo/ai/filmeto
PYTHONPATH=. python tests/test_agent_chat_history_signals_cli.py
```

### 2. `test_agent_chat_widget_history_signals.py` - GUI Test Application

A full GUI application that provides:
- Real-time chat list widget with historical messages loaded
- Control panel to simulate new messages via signals
- Live event logging
- Message statistics display

**Run:**
```bash
cd /Users/classfoo/ai/filmeto
PYTHONPATH=. python tests/test_agent_chat_widget_history_signals.py
```

Or use the quick launcher:
```bash
./tests/run_history_signal_test.sh
```

## What the GUI Test Shows

### Left Panel: Chat List Widget
- Displays historical messages loaded from `message.log`
- Shows messages grouped by `message_id`
- Auto-scrolls to bottom to show latest messages
- Virtualized rendering for performance

### Right Panel: Control Panel

#### Message Info Section
- Shows current message counts (active, archives, total)
- Shows how many messages are loaded in the UI
- "Refresh Info" button to update statistics

#### Simulate Messages Section
- **Send User Message**: Sends a user message via signals
- **Send Agent Message**: Sends an agent message via signals
- **Send Thinking Message**: Sends a thinking-type message via signals
- **Send Multi-Part Message**: Sends multiple parts (thinking + text) with the same `message_id` to test grouping
- **Send Batch of 5 Messages**: Sends 5 messages in quick succession

#### Polling Test Section
- Shows the polling mechanism status
- The chat list widget polls every 500ms for new messages
- Messages sent via signals are automatically saved to `message.log`
- The polling mechanism detects new messages and auto-loads them

#### Event Log Section
- Real-time log of all events
- Timestamps for each event
- Useful for debugging and understanding the flow

## How It Works

### Signal Flow
```
User clicks button
    ↓
Creates AgentMessage
    ↓
Sends via AgentChatSignals
    ↓
AgentChatHistoryListener receives signal
    ↓
Saves to message.log via FastMessageHistoryService
    ↓
Polling mechanism (in AgentChatListWidget) detects new messages
    ↓
Messages auto-load into the UI
```

### Message Grouping
Messages with the same `message_id` are grouped automatically:
- Example: A thinking process followed by a text response
- Both parts have the same `message_id`
- The UI displays them as a single message card
- This matches how the agent sends multi-part responses

## Test Results Summary

The CLI test shows:
```
✓ Connected to history
  Active log messages: 17
  Total messages (including archives): 17

✓ Loaded 17 raw messages from active log
✓ Grouped into 3 unique messages

✓ TEST PASSED: Message grouping working correctly
```

## Expected Behavior

1. **Initial Load**: When the GUI starts, historical messages are loaded from `message.log`
2. **New Messages**: Messages sent via the signal buttons are automatically:
   - Saved to `message.log`
   - Detected by the polling mechanism
   - Loaded into the UI automatically
3. **Message Grouping**: Messages with the same `message_id` are displayed as one message

## Troubleshooting

If messages don't appear:
1. Check the Event Log for errors
2. Click "Refresh Info" to see message counts
3. Verify the workspace/project path is correct
4. Check that `message.log` exists and is readable

## Related Files

- `agent/chat/history/agent_chat_storage.py` - Message log storage
- `agent/chat/history/agent_chat_history_service.py` - History service
- `agent/chat/history/agent_chat_history_listener.py` - Signal listener
- `agent/chat/agent_chat_signals.py` - Signal system
- `app/ui/chat/list/agent_chat_list.py` - Chat list widget
