# AgentMessageBubble Content Display Fix

## Problem

Text content in AgentMessageBubble was not displaying correctly. The bubble would appear but the text content would be invisible.

## Root Cause

The issue was in the Loader component's width binding in `AgentMessageBubble.qml`:

```qml
// Before (broken)
delegate: Loader {
    width: Math.max(0, contentColumn.width)  // contentColumn.width = 0 at init!
    // ...
}
```

The problem:
1. At initialization, `contentColumn.width` is 0
2. Loader's width becomes 0
3. Text widget inside Loader sets `width: parent ? parent.width : 0`
4. With width=0, the text is invisible even though content is correct

## Solution

Changed Loader to use anchors instead of explicit width binding:

```qml
// After (fixed)
delegate: Loader {
    anchors.left: parent.left
    anchors.right: parent.right
    // ...
}
```

This ensures:
- Loader always fills the parent column's width
- Text content inside the Loader gets proper width
- Text is visible and wraps correctly

## Files Changed

- `app/ui/chat/qml/components/AgentMessageBubble.qml`:
  - Line 166-170: Changed Loader width binding to use anchors

## Test Files Created

- `tests/test_app/test_ui/test_content_bubble.qml` - Full test interface
- `tests/test_app/test_ui/test_content_bubble_debug.qml` - Simplified debug test
- `tests/test_app/test_ui/test_content_display.py` - Python test runner
- `tests/test_app/test_ui/test_content_debug.py` - Debug test runner

## Running Tests

```bash
# Run debug test (3 scenarios)
python tests/test_app/test_ui/test_content_debug.py

# Run full test (10 content types)
python tests/test_app/test_ui/test_content_display.py
```

## Verification

Check each bubble in the test interface:
- [ ] Simple Text is visible
- [ ] Long Text wraps correctly
- [ ] Error displays properly
- [ ] Thinking content shows
- [ ] Code block renders
- [ ] Tool call displays
- [ ] Tool response shows
- [ ] Progress indicator works
- [ ] Typing indicator hidden (by design)
- [ ] Multiple content types display in sequence
