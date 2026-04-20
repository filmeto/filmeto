#!/usr/bin/env python3
"""
Test Bailian text2image ability
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.plugins.bailian_server.main import BailianServerPlugin

# Server configuration from workspace
SERVER_CONFIG = {
    "api_key": "sk-8f9dcabd81814ebe9f9c97a9eab3c3db",
    "coding_plan_enabled": True,
    "coding_plan_api_key": "sk-sp-e6404143920547bfbc2b0ea5df940039",
    "default_model": "qwen-max",
    "default_image_model": "qwen-image-2.0-pro"
}


async def test_text2image():
    """Test text2image ability"""
    plugin = BailianServerPlugin()

    # Task data
    task_data = {
        "task_id": "test-text2image-001",
        "ability": "text2image",
        "parameters": {
            "prompt": "A beautiful sunset over mountains, golden hour, dramatic clouds",
            "model": "wanx2.1-t2i-turbo",
            "width": 1024,
            "height": 1024
        },
        "metadata": {
            "server_config": SERVER_CONFIG
        }
    }

    # Progress callback
    def progress_callback(percent: float, message: str, data: dict):
        print(f"[{percent:.0f}%] {message}")

    print("Starting text2image test...")
    print(f"Prompt: {task_data['parameters']['prompt']}")
    print(f"Model: {task_data['parameters']['model']}")
    print(f"Size: {task_data['parameters']['width']}x{task_data['parameters']['height']}")
    print()

    try:
        result = await plugin.execute_task(task_data, progress_callback)
        print()
        print("Result:")
        print(f"  Status: {result.get('status')}")
        print(f"  Task ID: {result.get('task_id')}")

        if result.get('status') == 'success':
            print(f"  Output files: {result.get('output_files')}")
            if result.get('output_resources'):
                print(f"  Resources:")
                for r in result.get('output_resources'):
                    print(f"    - {r.get('type')}: {r.get('path')} ({r.get('size')} bytes)")
        else:
            print(f"  Error: {result.get('error_message')}")

        return result.get('status') == 'success'

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_text2image())
    sys.exit(0 if success else 1)