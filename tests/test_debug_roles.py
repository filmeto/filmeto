"""Debug script to check model roles."""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ['WORKSPACE_PATH'] = str(Path.cwd() / "workspace")

from PySide6.QtWidgets import QApplication
from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel
from app.ui.chat.list.agent_chat_list_widget import QmlAgentChatListWidget
from app.data.workspace import Workspace

def main():
    app = QApplication(sys.argv)

    workspace_path = str(Path.cwd() / "workspace")
    workspace = Workspace(workspace_path, "demo", defer_heavy_init=True)
    widget = QmlAgentChatListWidget(workspace, None)

    import time
    time.sleep(2)

    model = widget._model
    print(f"=== Model Row Count: {model.rowCount()} ===")

    print("\n=== Role Names ===")
    role_names = model.roleNames()
    for role_int, role_name in role_names.items():
        print(f"  {role_int} -> {role_name}")

    print("\n=== Sample Data ===")
    for i in range(min(3, model.rowCount())):
        print(f"\n--- Row {i} ---")
        index = model.index(i, 0)
        for role_int, role_name in role_names.items():
            data = model.data(index, role_int)
            if data and role_name in ["messageId", "senderName", "isUser", "content", "dateGroup"]:
                print(f"  {role_name}: {data}")

if __name__ == "__main__":
    main()
