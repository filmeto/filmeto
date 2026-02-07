"""Unit test for _load_message_from_history logic."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
from agent.chat.agent_chat_types import MessageType, ContentType
from agent.chat.content import StructureContent


def simulate_load_message_from_history(msg_data):
    """Simulate the _load_message_from_history method logic."""
    try:
        from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage

        metadata = msg_data.get("metadata", {})
        content_list = msg_data.get("content", [])

        # Extract basic info
        message_id = metadata.get("message_id", "")
        sender_id = metadata.get("sender_id", "unknown")
        sender_name = metadata.get("sender_name", sender_id)
        message_type_str = metadata.get("message_type", "text")

        if not message_id:
            print("  ✗ No message_id")
            return False

        # Parse message_type
        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            message_type = MessageType.TEXT

        # Check if this is a user message
        is_user = sender_id.lower() == "user"

        print(f"  Processing: {message_id}")
        print(f"    Sender: {sender_name} ({sender_id})")
        print(f"    Type: {message_type.value}")
        print(f"    Is User: {is_user}")

        if is_user:
            # For user messages, extract text from content
            text_content = ""
            for content_item in content_list:
                if isinstance(content_item, dict):
                    if content_item.get("content_type") == "text":
                        text_content = content_item.get("data", {}).get("text", "")
                        break
            print(f"    User text: {text_content[:50]}...")
        else:
            # Reconstruct structured content from content list
            structured_content = []
            for content_item in content_list:
                if isinstance(content_item, dict):
                    try:
                        sc = StructureContent.from_dict(content_item)
                        structured_content.append(sc)
                    except Exception as e:
                        print(f"    Warning: Failed to load structured content: {e}")

            # Create AgentMessage
            agent_message = ChatAgentMessage(
                message_type=message_type,
                sender_id=sender_id,
                sender_name=sender_name,
                message_id=message_id,
                metadata=metadata,
                structured_content=structured_content,
            )

            print(f"    Agent message created with {len(agent_message.structured_content)} items")
            print(f"    Text content: {agent_message.get_text_content()[:50] if agent_message.get_text_content() else '(empty)'}...")

        print(f"    ✓ Successfully loaded")
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_messages():
    """Test loading messages using the simulated logic."""
    workspace_path = "/Users/classfoo/ai/filmeto/workspace"
    project_name = "demo"

    print("=" * 70)
    print("Testing _load_message_from_history logic")
    print("=" * 70)

    try:
        # Get latest messages
        messages = FastMessageHistoryService.get_latest_messages(
            workspace_path, project_name, count=10
        )

        print(f"\nLoaded {len(messages)} messages from history\n")

        success_count = 0
        fail_count = 0

        for i, msg_data in enumerate(messages):
            print(f"[Message {i+1}]")
            if simulate_load_message_from_history(msg_data):
                success_count += 1
            else:
                fail_count += 1
            print()

        print("=" * 70)
        print(f"Results: {success_count} succeeded, {fail_count} failed")
        print("=" * 70)

        if fail_count == 0:
            print("✓ All messages loaded successfully!")
            return True
        else:
            print(f"✗ {fail_count} messages failed to load")
            return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_load_messages()
    sys.exit(0 if success else 1)
