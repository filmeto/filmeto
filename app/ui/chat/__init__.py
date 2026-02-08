"""Chat UI components for agent panel.

This package provides UI components for the agent chat interface:
- AgentChatListWidget: QML-based virtualized chat list widget
- AgentChatPlanWidget: Plan display and status tracking
"""

# Lazy loading - do not import at package level
# Import directly from submodules when needed:
#   from app.ui.chat.list import AgentChatListWidget
#   from app.ui.chat.plan import AgentChatPlanWidget

__all__ = [
    # Chat list (QML-based)
    'AgentChatListWidget',
    # Plan widgets
    'AgentChatPlanWidget',
    'StatusIconWidget',
    'StatusCountWidget',
    'PlanTaskRow',
    'ClickableFrame',
]
