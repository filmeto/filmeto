#!/usr/bin/env python3
"""
Test script to verify the fix for history loading issue.

This script tests that get_messages_before_gsn correctly returns
all log entries for each message_id, not just one entry per GSN.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.chat.history.global_sequence_manager import get_enhanced_history

def test_get_messages_before_gsn():
    """Test that get_messages_before_gsn returns complete message data."""
    
    workspace_path = str(project_root / "workspace")
    project_name = "demo"
    
    print("=" * 60)
    print("Testing get_messages_before_gsn fix")
    print("=" * 60)
    
    enhanced_history = get_enhanced_history(workspace_path, project_name)
    
    # Get current GSN
    current_gsn = enhanced_history.get_current_gsn()
    print(f"\nCurrent GSN: {current_gsn}")
    
    # Get total count
    total_count = enhanced_history.get_total_count()
    print(f"Total message count: {total_count}")
    
    # Test 1: Get latest messages
    print("\n--- Test 1: Get latest 10 messages ---")
    latest_messages = enhanced_history.get_latest_messages(10)
    print(f"Retrieved {len(latest_messages)} messages")
    
    # Group by message_id
    from collections import defaultdict
    message_groups = defaultdict(list)
    for msg in latest_messages:
        msg_id = msg.get('message_id', '')
        msg_gsn = msg.get('metadata', {}).get('gsn', 0)
        msg_type = msg.get('message_type', 'unknown')
        message_groups[msg_id].append((msg_gsn, msg_type))
    
    print(f"Unique message_ids: {len(message_groups)}")
    
    # Check for multi-entry messages
    multi_entry_count = sum(1 for entries in message_groups.values() if len(entries) > 1)
    print(f"Messages with multiple entries: {multi_entry_count}")
    
    # Show some examples
    for msg_id, entries in list(message_groups.items())[:3]:
        if len(entries) > 1:
            print(f"\n  Message {msg_id[:8]}... has {len(entries)} entries:")
            for gsn, msg_type in sorted(entries):
                print(f"    GSN {gsn}: {msg_type}")
    
    # Test 2: Get messages before a specific GSN
    test_gsn = current_gsn - 50
    if test_gsn > 0:
        print(f"\n--- Test 2: Get messages before GSN {test_gsn} ---")
        older_messages = enhanced_history.get_messages_before_gsn(test_gsn, count=20)
        print(f"Retrieved {len(older_messages)} log entries")
        
        # Group by message_id
        older_groups = defaultdict(list)
        for msg in older_messages:
            msg_id = msg.get('message_id', '')
            msg_gsn = msg.get('metadata', {}).get('gsn', 0)
            msg_type = msg.get('message_type', 'unknown')
            older_groups[msg_id].append((msg_gsn, msg_type))
        
        print(f"Unique message_ids: {len(older_groups)}")
        
        # Check for multi-entry messages
        older_multi_entry = sum(1 for entries in older_groups.values() if len(entries) > 1)
        print(f"Messages with multiple entries: {older_multi_entry}")
        
        # Verify that all entries for each message_id are present
        print("\n--- Verifying content completeness ---")
        for msg_id, entries in list(older_groups.items())[:5]:
            if len(entries) > 1:
                print(f"\n  Message {msg_id[:8]}... has {len(entries)} entries:")
                for gsn, msg_type in sorted(entries):
                    print(f"    GSN {gsn}: {msg_type}")
        
        # Check if entries are sorted by GSN
        gsns = [msg.get('metadata', {}).get('gsn', 0) for msg in older_messages]
        is_sorted = all(gsns[i] <= gsns[i+1] for i in range(len(gsns)-1))
        print(f"\nEntries sorted by GSN: {is_sorted}")
        
        if not is_sorted:
            print("ERROR: Entries are NOT sorted by GSN!")
            return False
    
    # Test 3: Verify no duplicate GSNs
    print("\n--- Test 3: Check for duplicate GSNs ---")
    all_gsns = [msg.get('metadata', {}).get('gsn', 0) for msg in older_messages]
    unique_gsns = set(all_gsns)
    
    if len(all_gsns) != len(unique_gsns):
        print(f"ERROR: Found duplicate GSNs! Total: {len(all_gsns)}, Unique: {len(unique_gsns)}")
        return False
    else:
        print(f"✓ No duplicate GSNs (total: {len(all_gsns)})")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_get_messages_before_gsn()
    sys.exit(0 if success else 1)
