"""Test script for agent_chat_list message loading functionality."""

import sys
import os

# Set PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.chat.history.agent_chat_history_service import AgentChatHistoryService
from agent.chat.content import StructureContent


def test_message_structure_loading():
    """Test loading and parsing message structures from history."""
    workspace_path = "/Users/classfoo/ai/filmeto/workspace"
    project_name = "demo"

    print(f"Testing message structure loading for project: {project_name}")
    print("=" * 70)

    try:
        # Get latest messages
        messages = AgentChatHistoryService.get_latest_messages(
            workspace_path, project_name, count=5
        )

        print(f"\n✓ Loaded {len(messages)} messages\n")

        for i, msg_data in enumerate(messages):
            print(f"[Message {i+1}]")
            print("-" * 70)

            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("content", [])

            # Extract basic info
            message_id = metadata.get("message_id", "")
            sender_id = metadata.get("sender_id", "unknown")
            sender_name = metadata.get("sender_name", sender_id)
            message_type_str = metadata.get("message_type", "text")

            print(f"  Message ID: {message_id}")
            print(f"  Sender: {sender_name} ({sender_id})")
            print(f"  Type: {message_type_str}")

            # Check if user message
            is_user = sender_id.lower() == "user"
            print(f"  Is User: {is_user}")

            if is_user:
                # For user messages, extract text from content
                text_content = ""
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        if content_item.get("content_type") == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                            break
                print(f"  Text Content: {text_content[:100]}...")
            else:
                # Reconstruct structured content from content list
                print(f"  Structured Content Items: {len(content_list)}")
                structured_content = []
                for j, content_item in enumerate(content_list):
                    if isinstance(content_item, dict):
                        try:
                            sc = StructureContent.from_dict(content_item)
                            structured_content.append(sc)
                            print(f"    [{j+1}] {sc.content_type.value}: {sc.title or 'No title'}")
                        except Exception as e:
                            print(f"    [{j+1}] Failed to load: {e}")

                print(f"  Successfully loaded {len(structured_content)} structured content items")

            print()

        # Test message after check
        print("=" * 70)
        print("\n[Test] Getting messages after a specific message...")

        if messages:
            # Use the second to last message as reference
            ref_msg = messages[-1] if len(messages) > 1 else messages[0]
            ref_metadata = ref_msg.get("metadata", {})
            ref_message_id = ref_metadata.get("message_id")

            if ref_message_id:
                messages_after = AgentChatHistoryService.get_messages_after(
                    workspace_path, project_name, ref_message_id, count=3
                )

                print(f"  Reference message ID: {ref_message_id}")
                print(f"  Messages after: {len(messages_after)}")

                for msg in messages_after:
                    m = msg.get("metadata", {})
                    print(f"    - {m.get('sender_name')}: {m.get('message_id')}")

        print("\n" + "=" * 70)
        print("✓ All message structure tests passed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_message_parsing():
    """Test parsing individual message from history data."""
    print("\n" + "=" * 70)
    print("[Test] Testing individual message parsing")
    print("=" * 70)

    workspace_path = "/Users/classfoo/ai/filmeto/workspace"
    project_name = "demo"

    try:
        messages = AgentChatHistoryService.get_latest_messages(
            workspace_path, project_name, count=1
        )

        if not messages:
            print("✗ No messages found")
            return False

        msg_data = messages[0]
        metadata = msg_data.get("metadata", {})
        content_list = msg_data.get("content", [])

        print(f"\nParsing message: {metadata.get('message_id')}")
        print(f"  Sender: {metadata.get('sender_name')}")
        print(f"  Content items: {len(content_list)}")

        # Test parsing message_type
        from agent.chat.agent_chat_types import MessageType
        message_type_str = metadata.get("message_type", "text")
        try:
            message_type = MessageType(message_type_str)
            print(f"  Parsed message_type: {message_type}")
        except ValueError:
            message_type = MessageType.TEXT
            print(f"  Defaulted to TEXT type")

        # Test reconstructing structured content
        structured_content = []
        for content_item in content_list:
            if isinstance(content_item, dict):
                try:
                    sc = StructureContent.from_dict(content_item)
                    structured_content.append(sc)
                except Exception as e:
                    print(f"  Warning: Failed to parse content item: {e}")

        print(f"  Successfully reconstructed {len(structured_content)} structured content items")

        # Test constructing AgentMessage
        from agent.chat.agent_chat_message import AgentMessage
        from datetime import datetime

        agent_message = AgentMessage(
            message_type=message_type,
            sender_id=metadata.get("sender_id", "unknown"),
            sender_name=metadata.get("sender_name", ""),
            message_id=metadata.get("message_id", ""),
            metadata=metadata,
            structured_content=structured_content,
        )

        print(f"\n  Created AgentMessage:")
        print(f"    - message_type: {agent_message.message_type}")
        print(f"    - sender_id: {agent_message.sender_id}")
        print(f"    - sender_name: {agent_message.sender_name}")
        print(f"    - message_id: {agent_message.message_id}")
        print(f"    - structured_content: {len(agent_message.structured_content)} items")

        # Test getting text content
        text_content = agent_message.get_text_content()
        print(f"    - text_content: {text_content[:100] if text_content else '(empty)'}...")

        print("\n✓ Message parsing test passed!")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_message_structure_loading()
    success2 = test_message_parsing()

    sys.exit(0 if (success1 and success2) else 1)
