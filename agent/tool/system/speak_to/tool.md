# speak_to

Send messages between crew members with different visibility modes.

## Description

This tool enables crew members to communicate with each other through FilmetoAgent's message routing system. It supports three communication modes with different visibility and routing behaviors.

## Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| mode | string | Yes | Communication mode: "public", "specify", or "private" |
| message | string | Yes | The message content to send |
| target | string | Conditional | Target crew member name (required for "specify" and "private" modes) |

## Modes

### public
- Message is sent to FilmetoAgent and processed through normal routing logic
- Visible to all crew members in the conversation history
- May be handled by producer or any relevant crew member

### specify
- Message starts with @mention format (e.g., "@director please review this")
- Visible to all crew members in the conversation history
- Typically routed to and handled by the mentioned crew member

### private
- Message is sent directly to the target crew member
- NOT recorded in conversation history
- NOT processed through FilmetoAgent's routing logic
- Used for direct, private communication between crew members

## Examples

### Public message
```json
{
    "mode": "public",
    "message": "I have completed the scene analysis. Ready for review."
}
```

### Specify message
```json
{
    "mode": "specify",
    "target": "director",
    "message": "Please review the storyboard I just created."
}
```

### Private message
```json
{
    "mode": "private",
    "target": "cinematographer",
    "message": "Can you help me with the lighting setup for scene 5?"
}
```

## Returns

| Field | Type | Description |
|-------|------|-------------|
| mode | string | The communication mode used |
| success | boolean | Whether the message was sent successfully |
| target | string | Target crew member (for specify/private modes) |
| message | string | Success message |
| message_id | string | Unique identifier for the message |

## Notes

- The sender should not send messages to themselves (especially for producer)
- Private messages bypass history recording for confidentiality
- Specify mode uses @mention format for clear targeting while maintaining visibility
