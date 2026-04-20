from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.ui.chat.agent_chat import AgentChatWidget, GROUP_CHAT_TAB_INDEX


def test_on_tab_changed_refreshes_group_chat_when_returning(monkeypatch) -> None:
    class _DummyPrivateChat:
        def __init__(self):
            self.active_calls = []

        def set_active(self, active: bool):
            self.active_calls.append(active)

    # _on_tab_changed imports this symbol at call time; patch it so isinstance()
    # works with our lightweight dummy widget.
    monkeypatch.setattr(
        "app.ui.chat.private_chat_widget.PrivateChatWidget",
        _DummyPrivateChat,
    )

    private_widget = _DummyPrivateChat()
    refreshed = {"count": 0}

    class _DummyTabWidget:
        def count(self):
            return 2

        def widget(self, i):
            if i == 1:
                return private_widget
            return None

    fake = SimpleNamespace(
        tab_widget=_DummyTabWidget(),
        chat_history_widget=SimpleNamespace(
            on_became_active=lambda: refreshed.__setitem__("count", refreshed["count"] + 1)
        ),
    )

    AgentChatWidget._on_tab_changed(fake, GROUP_CHAT_TAB_INDEX)

    assert private_widget.active_calls == [False]
    assert refreshed["count"] == 1

