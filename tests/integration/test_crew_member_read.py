#!/usr/bin/env python3
"""Test script to verify crew_member_read parsing from history."""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/classfoo/ai/filmeto')

from app.ui.chat.list.builders.message_builder import MessageBuilder
from app.ui.chat.list.managers.metadata_resolver import MetadataResolver


# Sample history data from the user
raw_messages = [
    # User message "你好"
    {
        "message_id": "4827e704-1a2f-4ec7-8f5f-52e242c10eea",
        "message_type": "text",
        "sender_id": "user",
        "sender_name": "User",
        "timestamp": "2026-03-05T23:27:31.740739",
        "metadata": {
            "session_id": "4b0f37b6-93b9-47e2-9c02-d75f53d6afc3",
            "gsn": 1
        },
        "content": [
            {
                "content_id": "697369c8-fa1c-46d8-8c1d-1f11528f3843",
                "content_type": "text",
                "title": None,
                "description": None,
                "data": {"text": "你好"},
                "metadata": {},
                "status": "creating",
                "parent_id": None
            }
        ]
    },
    # crew_member_read for user message
    {
        "message_id": "4827e704-1a2f-4ec7-8f5f-52e242c10eea",
        "message_type": "crew_member_read",
        "sender_id": "user",
        "sender_name": "User",
        "timestamp": "2026-03-05T23:28:07.618132",
        "metadata": {
            "session_id": "4b0f37b6-93b9-47e2-9c02-d75f53d6afc3",
            "event_type": "crew_member_read",
            "gsn": 2
        },
        "content": [
            {
                "content_id": "34bac233-abc6-4030-b590-3cadd3304021",
                "content_type": "crew_member_read",
                "title": None,
                "description": None,
                "data": {
                    "crew_members": [
                        {"id": "王小林", "name": "王小林", "icon": "💼", "color": "#7b68ee"}
                    ]
                },
                "metadata": {},
                "status": "creating",
                "parent_id": None
            }
        ]
    },
    # Agent message from 王小林
    {
        "message_id": "46ed4efe-247d-48c6-886d-30ccda10aa7a",
        "message_type": "text",
        "sender_id": "王小林",
        "sender_name": "王小林",
        "timestamp": "2026-03-05T23:28:14.227211",
        "metadata": {
            "session_id": "4b0f37b6-93b9-47e2-9c02-d75f53d6afc3",
            "gsn": 3
        },
        "content": [
            {
                "content_id": "fda5f4c3-92c8-4733-b58d-47d6b6d180cb",
                "content_type": "text",
                "title": "Final Response",
                "description": "ReAct process completed successfully",
                "data": {"text": "你好！我是王小林，影视项目管理专家，很高兴为您服务！"},
                "metadata": {},
                "status": "creating",
                "parent_id": None
            }
        ]
    },
    # crew_member_read for agent message
    {
        "message_id": "46ed4efe-247d-48c6-886d-30ccda10aa7a",
        "message_type": "crew_member_read",
        "sender_id": "王小林",
        "sender_name": "王小林",
        "timestamp": "2026-03-05T23:30:31.024626",
        "metadata": {
            "session_id": "4b0f37b6-93b9-47e2-9c02-d75f53d6afc3",
            "event_type": "crew_member_read",
            "gsn": 4
        },
        "content": [
            {
                "content_id": "9a32ddde-8067-4d5d-9f71-bdec3e94af9f",
                "content_type": "crew_member_read",
                "title": None,
                "description": None,
                "data": {
                    "crew_members": [
                        {"id": "许小华", "name": "许小华", "icon": "🎬", "color": "#4a90e2"},
                        {"id": "芦小苇", "name": "芦小苇", "icon": "✍️", "color": "#32cd32"}
                    ]
                },
                "metadata": {},
                "status": "creating",
                "parent_id": None
            }
        ]
    },
]


class MockMetadataResolver:
    """Mock metadata resolver for testing."""
    _crew_member_metadata = {}

    def load_crew_member_metadata(self):
        pass


def main():
    print("=" * 60)
    print("Testing crew_member_read parsing from history")
    print("=" * 60)

    # Create a mock metadata resolver
    resolver = MockMetadataResolver()

    # Create a mock model (just needs roleNames method)
    class MockModel:
        STRUCTURED_CONTENT = "structuredContent"

        def get_row_by_message_id(self, message_id):
            return None

        def get_item(self, row):
            return None

        def update_item(self, message_id, updates):
            pass

    model = MockModel()

    # Create message builder
    builder = MessageBuilder(resolver, model)

    # Build items from raw messages
    print("\n=== Building items from raw messages ===\n")
    items = builder.build_items_from_raw_messages(raw_messages)

    print(f"\n=== Results: {len(items)} items built ===\n")

    for i, item in enumerate(items):
        print(f"Item {i + 1}:")
        print(f"  message_id: {item.message_id[:8]}...")
        print(f"  sender_id: {item.sender_id}")
        print(f"  sender_name: {item.sender_name}")
        print(f"  is_user: {item.is_user}")
        print(f"  crew_read_by: {item.crew_read_by}")
        print()


if __name__ == "__main__":
    main()