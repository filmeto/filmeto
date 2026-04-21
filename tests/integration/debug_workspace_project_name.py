"""
Debug workspace project_name issue.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

print("=" * 70)
print("Debug Workspace Project Name")
print("=" * 70)

from app.data.workspace import Workspace
from agent.chat.history.agent_chat_storage import MessageLogHistory
from agent.chat.history.agent_chat_history_service import FastMessageHistoryService

workspace_path = str(project_root / "workspace")
project_name = "demo"

print(f"\nTest 1: Direct MessageLogHistory creation")
print("-" * 70)

# Direct creation
history1 = MessageLogHistory(workspace_path, project_name)
messages1 = history1.get_latest_messages(count=10)
print(f"  Direct creation: {len(messages1)} messages")

print(f"\nTest 2: FastMessageHistoryService.get_history()")
print("-" * 70)

# Through service
history2 = FastMessageHistoryService.get_history(workspace_path, project_name)
messages2 = history2.get_latest_messages(count=10)
print(f"  Through service: {len(messages2)} messages")

print(f"\nTest 3: Workspace object")
print("-" * 70)

# Create workspace with correct parameter order
workspace = Workspace(workspace_path, project_name)

print(f"  Workspace object created")
print(f"  workspace.workspace_path: {workspace.workspace_path}")
print(f"  workspace.project_name: {workspace.project_name}")

# Get what the widget would use
widget_workspace_path = workspace.workspace_path
widget_project_name = workspace.project_name

print(f"\n  Widget would use:")
print(f"    workspace_path: {widget_workspace_path}")
print(f"    project_name: {widget_project_name}")

# Test with those values
history3 = FastMessageHistoryService.get_history(widget_workspace_path, widget_project_name)
messages3 = history3.get_latest_messages(count=10)
print(f"  Messages with workspace values: {len(messages3)}")

print(f"\nTest 4: Check service key")
print("-" * 70)

key = FastMessageHistoryService._make_key(widget_workspace_path, widget_project_name)
print(f"  Service key: '{key}'")

if key in FastMessageHistoryService._instances:
    print(f"  ✓ Key found in instances")
    cached_history = FastMessageHistoryService._instances[key]
    messages4 = cached_history.get_latest_messages(count=10)
    print(f"  Cached history returns: {len(messages4)} messages")
else:
    print(f"  ✗ Key NOT found in instances")
    print(f"  Available keys: {list(FastMessageHistoryService._instances.keys())}")

print("\n" + "=" * 70)
print("Debug Complete")
print("=" * 70)
