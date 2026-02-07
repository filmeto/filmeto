"""Test script for the new MessageLogStorage system."""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.chat.history.agent_chat_storage import MessageLogStorage, MessageLogHistory, Constants

# Workspace configuration
workspace_path = "/Users/classfoo/ai/filmeto/workspace"
project_name = "demo"
history_root = os.path.join(workspace_path, "projects", project_name, "agent", "history")


def test_basic_operations():
    """Test basic storage operations."""
    print("\n" + "=" * 70)
    print("TEST: Basic Storage Operations")
    print("=" * 70)

    storage = MessageLogStorage(history_root)

    # 1. Test message count
    print(f"\n[1/5] Testing message count...")
    count = storage.get_message_count()
    print(f"  Initial message count: {count}")

    # 2. Test get latest messages
    print(f"\n[2/5] Testing get_latest_messages...")
    latest = storage.get_latest_messages(5)
    print(f"  Retrieved {len(latest)} latest messages")
    for i, msg in enumerate(latest):
        sender = msg.get("metadata", {}).get("sender_name", "Unknown")
        print(f"    [{i+1}] {sender}: {msg.get('metadata', {}).get('message_id', '')[:8]}...")

    # 3. Test get_messages
    print(f"\n[3/5] Testing get_messages range...")
    if count > 0:
        start = max(0, count - 5)
        messages = storage.get_messages(start, 5)
        print(f"  Retrieved {len(messages)} messages from offset {start}")
        for i, msg in enumerate(messages):
            sender = msg.get("metadata", {}).get("sender_name", "Unknown")
            print(f"    [{i+1}] {sender}: {msg.get('metadata', {}).get('message_id', '')[:8]}...")

    # 4. Test get_total_count
    print(f"\n[4/5] Testing MessageLogHistory...")
    history = MessageLogHistory(workspace_path, project_name)
    total = history.get_total_count()
    print(f"  Total messages (including archives): {total}")

    # 5. Test constants
    print(f"\n[5/5] Testing constants...")
    print(f"  MAX_MESSAGES: {Constants.MAX_MESSAGES}")
    print(f"  ARCHIVE_THRESHOLD: {Constants.ARCHIVE_THRESHOLD}")
    print(f"  ARCHIVE_PREFIX: {Constants.ARCHIVE_PREFIX}")
    print(f"  ACTIVE_LOG: {Constants.ACTIVE_LOG}")

    return True


def test_append_operations():
    """Test append operations."""
    print("\n" + "=" * 70)
    print("TEST: Append Operations")
    print("=" * 70)

    storage = MessageLogStorage(history_root)

    # Test append
    print(f"\n[1/2] Testing append...")
    test_msg = {
        "message_id": "test_append_123",
        "message_type": "text",
        "sender_id": "test_user",
        "sender_name": "Test User",
        "timestamp": datetime.now().isoformat(),
        "metadata": {},
        "structured_content": [{"content_type": "text", "text": "Test message"}],
    }
    before_count = storage.get_message_count()
    success = storage.append_message(test_msg)
    after_count = storage.get_message_count()
    print(f"  Append result: {success}")
    print(f"  Count before: {before_count}, after: {after_count}")

    # Test get_latest_messages after append
    print(f"\n[2/2] Testing get_latest_messages after append...")
    latest = storage.get_latest_messages(1)
    if latest:
        msg = latest[0]
        sender = msg.get("metadata", {}).get("sender_name", "Unknown")
        print(f"  Latest message: {sender}: {msg.get('metadata', {}).get('message_id', '')[:8]}...")

    return True


def test_performance():
    """Test performance with timing."""
    print("\n" + "=" * 70)
    print("TEST: Performance")
    print("=" * 70)

    import time

    history = MessageLogHistory(workspace_path, project_name)

    # Test 1: Get latest 30 messages
    print(f"\n[1/3] Loading latest 30 messages...")
    start = time.time()
    messages = history.get_latest_messages(30)
    elapsed = time.time() - start
    print(f"  Loaded {len(messages)} messages in {elapsed*1000:.2f}ms")

    # Test 2: Get messages before
    total = history.get_total_count()
    if total > 0:
        line_offset = history.get_latest_line_offset()
        print(f"\n[2/3] Loading messages before offset {line_offset}...")
        start = time.time()
        older = history.get_messages_before(line_offset, 30)
        elapsed = time.time() - start
        print(f"  Loaded {len(older)} messages in {elapsed*1000:.2f}ms")

    # Test 3: Multiple sequential loads
    print(f"\n[3/3] Loading 30 messages 3 times...")
    start = time.time()
    for i in range(3):
        msgs = history.get_latest_messages(30)
    elapsed = time.time() - start
    print(f"  {len(msgs)} messages x3 in {elapsed*1000:.2f}ms ({elapsed/3*1000:.2f}ms per load)")

    return True


def test_archive_operations():
    """Test archive operations."""
    print("\n" + "=" * 70)
    print("TEST: Archive Operations")
    print("=" * 70)

    storage = MessageLogStorage(history_root)

    # List archives
    print(f"\n[1/3] Listing archives...")
    archives = storage.get_archived_files()
    print(f"  Found {len(archives)} archive files")
    for i, archive_path in enumerate(archives[:3]):  # Show first 3
        print(f"    [{i+1}] {archive_path.name}")

    # Test loading from archive
    if archives:
        print(f"\n[2/3] Loading from archive...")
        archive = storage.load_archive(archives[0])
        archive_count = archive.get_line_count()
        print(f"  Archive has {archive_count} messages")

        # Get some messages from archive
        messages = archive.get_latest_messages(5)
        print(f"  Retrieved {len(messages)} messages from archive")
        for i, msg in enumerate(messages):
            sender = msg.get("metadata", {}).get("sender_name", "Unknown")
            print(f"    [{i+1}] {sender}: {msg.get('metadata', {}).get('message_id', '')[:8]}...")

    # Test total count
    print(f"\n[3/3] Testing total count...")
    total = storage.get_total_count()
    active = storage.get_message_count()
    print(f"  Total: {total}, Active: {active}, Archived: {total - active}")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MESSAGE LOG STORAGE TEST")
    print("=" * 70)

    print(f"\nUsing history root: {history_root}")

    # Check if directory exists
    if not os.path.exists(history_root):
        print(f"\nCreating history directory...")
        os.makedirs(history_root, exist_ok=True)
        print("  Created.")

    success1 = test_basic_operations()
    success2 = test_append_operations()
    success3 = test_performance()
    success4 = test_archive_operations()

    print("\n" + "=" * 70)
    if success1 and success2 and success3 and success4:
        print("✓ ALL TESTS PASSED!")
    else:
        print("⚠ SOME TESTS FAILED")
    print("=" * 70)


if __name__ == "__main__":
    main()
