#!/usr/bin/env python3
"""Test with actual workspace history data."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def test_real_history():
    """Test loading actual history data from workspace."""

    print("\n" + "=" * 70)
    print(" Real History Data Test")
    print("=" * 70)

    # Try to find the workspace path
    # Common locations: ~/.filmeto_workspace or ./workspace
    workspace_path = os.path.expanduser("~/.filmeto_workspace")
    if not os.path.exists(workspace_path):
        workspace_path = os.path.join(project_root, "workspace")

    print(f"[INFO] Checking workspace path: {workspace_path}")

    if not os.path.exists(workspace_path):
        print(f"[WARNING] Workspace path does not exist: {workspace_path}")
        print("Please ensure the workspace is initialized.")
        return False

    # Find projects
    projects_dir = os.path.join(workspace_path, "projects")
    if not os.path.exists(projects_dir):
        print(f"[WARNING] Projects directory not found: {projects_dir}")
        return False

    # List all projects
    project_names = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
    if not project_names:
        print("[WARNING] No projects found in workspace")
        return False

    print(f"[INFO] Found projects: {project_names}")

    # Use the first project
    project_name = project_names[0]
    print(f"[INFO] Using project: {project_name}")

    # Get history
    from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

    history = FastMessageHistoryService.get_history(workspace_path, project_name)

    # Get latest messages
    messages = history.get_latest_messages(count=5)

    print(f"\n[INFO] Found {len(messages)} messages in history")

    if not messages:
        print("\n[WARNING] No messages found in history")
        print("The history storage is empty.")
        print("\nThis is why you're not seeing any content!")
        print("Try sending a message first to create history data.")
        return False

    # Display each message
    for i, msg in enumerate(messages):
        print(f"\n--- Message {i+1} ---")
        print(f"Keys: {list(msg.keys())}")
        print(f"sender_name: {msg.get('sender_name')}")
        print(f"timestamp: {msg.get('timestamp')}")

        # Check content fields
        structured_content = msg.get('structured_content')
        content = msg.get('content')

        if structured_content:
            print(f"structured_content: {len(structured_content)} items")
            for j, item in enumerate(structured_content):
                if isinstance(item, dict):
                    ct = item.get('content_type')
                    data = item.get('data', {})
                    print(f"  [{j}] content_type={ct}")
                    if ct == 'text':
                        print(f"      text: {data.get('text', '')[:50]}...")
        elif content:
            print(f"content: {len(content)} items (old format)")
        else:
            print("No content found!")

    return True


if __name__ == "__main__":
    try:
        success = test_real_history()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
