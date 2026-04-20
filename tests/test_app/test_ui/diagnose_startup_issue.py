#!/usr/bin/env python3
"""诊断 startup 窗口历史消息显示问题"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def check_agent_message_bubble():
    """检查 AgentMessageBubble.qml 的文本提取逻辑"""
    print("\n" + "=" * 70)
    print(" 检查 1: AgentMessageBubble.qml 文本提取逻辑")
    print("=" * 70)

    qml_file = project_root / "app" / "ui" / "chat" / "qml" / "components" / "AgentMessageBubble.qml"

    if not qml_file.exists():
        print(f"[ERROR] 文件不存在: {qml_file}")
        return False

    with open(qml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否包含修复的文本提取逻辑
    has_safeget_fix = 'root.safeGet(data, "text"' in content and 'root.safeGet(data, "content"' in content
    has_nested_fix = 'root.safeGetData(data, {})' in content

    print(f"[INFO] 文件路径: {qml_file}")
    print(f"[INFO] 文件大小: {len(content)} bytes")
    print(f"[INFO] 包含 safeGet 文本提取: {'✓' if has_safeget_fix else '✗'}")
    print(f"[INFO] 包含嵌套数据提取: {'✓' if has_nested_fix else '✗'}")

    if not (has_safeget_fix and has_nested_fix):
        print("\n[WARNING] AgentMessageBubble.qml 可能不是最新版本！")
        print("          文本提取逻辑可能不完整。")
        return False

    print("\n[SUCCESS] AgentMessageBubble.qml 包含最新的文本提取逻辑")
    return True


def check_qml_cache():
    """检查 QML 缓存"""
    print("\n" + "=" * 70)
    print(" 检查 2: QML 缓存")
    print("=" * 70)

    cache_locations = [
        Path.home() / ".cache" / "QtProject",
        Path.home() / ".cache" / "Qt",
        Path("/tmp") / "qmlcache",
    ]

    found_cache = False
    for cache_path in cache_locations:
        if cache_path.exists():
            print(f"[INFO] 找到缓存: {cache_path}")
            print(f"       大小: {sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file()) / 1024 / 1024:.2f} MB")
            found_cache = True

    if not found_cache:
        print("[INFO] 未找到 QML 缓存目录")

    return found_cache


def test_startup_flow():
    """测试 startup 窗口数据流程"""
    print("\n" + "=" * 70)
    print(" 检查 3: Startup 窗口数据流程")
    print("=" * 70)

    try:
        from agent.chat.history.agent_chat_history_service import FastMessageHistoryService
        from agent.chat.content import StructureContent
        from agent import AgentMessage
        from app.ui.chat.list.agent_chat_list_items import ChatListItem
        from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

        workspace_path = os.path.expanduser("~/.filmeto_workspace")
        if not os.path.exists(workspace_path):
            workspace_path = os.path.join(project_root, "workspace")

        projects_dir = os.path.join(workspace_path, "projects")
        if not os.path.exists(projects_dir):
            print("[WARNING] Projects directory not found")
            return False

        project_names = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
        if not project_names:
            print("[WARNING] No projects found")
            return False

        project_name = project_names[0]
        history = FastMessageHistoryService.get_history(workspace_path, project_name)
        messages = history.get_latest_messages(count=1)

        if not messages:
            print("[WARNING] No messages found")
            return False

        msg_data = messages[0]
        metadata = msg_data.get("metadata", {})
        content_list = msg_data.get("structured_content") or msg_data.get("content", [])
        if not content_list:
            content_list = metadata.get("structured_content") or metadata.get("content", [])

        print(f"[INFO] 找到消息，内容项数: {len(content_list)}")

        # 解析内容
        structured_content = []
        for content_item in content_list:
            if isinstance(content_item, dict):
                try:
                    sc = StructureContent.from_dict(content_item)
                    structured_content.append(sc)
                except Exception as e:
                    print(f"[WARNING] Failed to parse content: {e}")

        if not structured_content:
            print("[WARNING] 无法解析内容")
            return False

        print(f"[INFO] 解析成功: {type(structured_content[0]).__name__}")

        # 转换为 QML 格式
        message_id = msg_data.get("message_id") or metadata.get("message_id", "")
        sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
        sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)

        agent_message = AgentMessage(
            sender_id=sender_id,
            sender_name=sender_name,
            message_id=message_id,
            structured_content=structured_content,
        )

        chat_item = ChatListItem(
            message_id=message_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_user=False,
            agent_message=agent_message,
        )

        qml_item = QmlAgentChatListModel.from_chat_list_item(chat_item)

        print(f"[INFO] QML 格式转换成功")
        print(f"[INFO] structuredContent 长度: {len(qml_item.get('structuredContent', []))}")

        if qml_item.get('structuredContent'):
            sc = qml_item['structuredContent'][0]
            print(f"[INFO] 第一项 content_type: {sc.get('content_type')}")
            print(f"[INFO] 第一项包含 'data': {'data' in sc}")
            if 'data' in sc and isinstance(sc['data'], dict):
                print(f"[INFO] 第一项包含 'text': {'text' in sc['data']}")
                if 'text' in sc['data']:
                    print(f"[INFO] 文本内容: {sc['data']['text'][:50]}...")
                    return True

        print("[WARNING] QML 数据格式异常")
        return False

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主诊断流程"""
    print("\n" + "=" * 70)
    print(" Startup 窗口历史消息显示问题诊断")
    print("=" * 70)

    results = []

    # 检查 1: QML 文件
    results.append(("AgentMessageBubble.qml", check_agent_message_bubble()))

    # 检查 2: QML 缓存
    has_cache = check_qml_cache()

    # 检查 3: 数据流程
    results.append(("数据流程", test_startup_flow()))

    # 总结
    print("\n" + "=" * 70)
    print(" 诊断结果")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    if has_cache:
        print(f"\n[建议] 发现 QML 缓存，建议清除:")
        print(f"  rm -rf ~/.cache/QtProject")
        print(f"  rm -rf ~/.cache/Qt")

    if all_passed:
        print("\n[SUCCESS] 所有检查通过！")
        print("\n如果 startup 窗口仍然无法显示历史消息，请：")
        print("  1. 清除 QML 缓存")
        print("  2. 重新启动应用")
        print("  3. 检查控制台调试输出")
    else:
        print("\n[ERROR] 部分检查失败，请根据上述提示进行修复。")

    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
