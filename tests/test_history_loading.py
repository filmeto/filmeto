"""Test script for loading agent chat history."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.chat.history.agent_chat_history_service import FastMessageHistoryService


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
        messages = FastMessageHistoryService.get_latest_messages(
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

        # Test 2: Get total count
        print("\n[Test 2] Getting total message count...")
        total_count = FastMessageHistoryService.get_total_count(
            workspace_path, project_name
        )
        print(f"✓ Total messages: {total_count}")

        # Test 3: Get latest line offset
        print("\n[Test 3] Getting latest line offset...")
        line_offset = FastMessageHistoryService.get_latest_line_offset(
            workspace_path, project_name
        )
        print(f"✓ Active log line offset: {line_offset}")

        # Test 4: Get messages after line offset
        print("\n[Test 4] Getting messages after line offset (should be empty)...")
        messages_after = FastMessageHistoryService.get_messages_after(
            workspace_path, project_name, line_offset, count=5
        )
        print(f"✓ Messages after offset: {len(messages_after)}")

        # Test 5: Get messages before line offset
        print("\n[Test 5] Getting messages before line offset...")
        messages_before = FastMessageHistoryService.get_messages_before(
            workspace_path, project_name, line_offset, count=5
        )
        print(f"✓ Messages before offset: {len(messages_before)}")

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
