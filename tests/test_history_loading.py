"""Test script for loading agent chat history."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.chat.history.agent_chat_history_service import AgentChatHistoryService


def test_load_history():
    """Test loading history from demo project."""
    workspace_path = "/Users/classfoo/ai/filmeto/workspace"
    project_name = "demo"

    print(f"Testing history loading for project: {project_name}")
    print(f"Workspace path: {workspace_path}")
    print("-" * 60)

    try:
        # Test 1: Get latest messages
        print("\n[Test 1] Getting latest 10 messages...")
        messages = AgentChatHistoryService.get_latest_messages(
            workspace_path, project_name, count=10
        )
        print(f"✓ Loaded {len(messages)} messages")

        if messages:
            print("\nFirst 3 messages:")
            for i, msg in enumerate(messages[:3]):
                metadata = msg.get("metadata", {})
                print(f"  {i+1}. ID: {metadata.get('message_id', 'N/A')}")
                print(f"     Sender: {metadata.get('sender_name', 'N/A')} ({metadata.get('sender_id', 'N/A')})")
                print(f"     Type: {metadata.get('message_type', 'N/A')}")
                content_list = msg.get("content", [])
                text_content = ""
                for c in content_list:
                    if isinstance(c, dict) and c.get("content_type") == "text":
                        text_content = c.get("data", {}).get("text", "")[:100]
                        break
                print(f"     Content: {text_content}...")
                print()

        # Test 2: Get latest message info
        print("\n[Test 2] Getting latest message info...")
        latest_info = AgentChatHistoryService.get_latest_message_info(
            workspace_path, project_name
        )
        if latest_info:
            print(f"✓ Latest message ID: {latest_info.get('message_id')}")
            print(f"  Timestamp: {latest_info.get('timestamp')}")
            print(f"  File: {latest_info.get('file_path')}")
        else:
            print("✗ No latest message info found")

        # Test 3: Get latest message ID
        print("\n[Test 3] Getting latest message ID...")
        latest_id = AgentChatHistoryService.get_latest_message_id(
            workspace_path, project_name
        )
        print(f"✓ Latest message ID: {latest_id}")

        # Test 4: Get messages after a specific message
        if latest_id:
            print("\n[Test 4] Getting messages after latest (should be empty)...")
            messages_after = AgentChatHistoryService.get_messages_after(
                workspace_path, project_name, latest_id, count=5
            )
            print(f"✓ Messages after latest: {len(messages_after)}")

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_load_history()
    sys.exit(0 if success else 1)
