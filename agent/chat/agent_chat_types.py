"""
Common enums for the agent module.
"""
from enum import Enum


class MessageType(Enum):
    """Enumeration of different message types."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    COMMAND = "command"
    ERROR = "error"
    SYSTEM = "system"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"


class ContentType(Enum):
    """Enumeration of different structured content types."""
    # === 基础内容 ===
    TEXT = "text"
    CODE_BLOCK = "code_block"

    # === 思考内容 ===
    THINKING = "thinking"

    # === 工具内容 ===
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"

    # === 多媒体内容 ===
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

    # === 数据展示 ===
    TABLE = "table"
    CHART = "chart"

    # === 交互元素 ===
    LINK = "link"
    BUTTON = "button"
    FORM = "form"

    # === 文件相关 ===
    FILE_ATTACHMENT = "file_attachment"

    # === 任务和计划 ===
    PLAN = "plan"
    STEP = "step"
    TASK_LIST = "task_list"
    SKILL = "skill"

    # === 状态和元数据 ===
    PROGRESS = "progress"
    METADATA = "metadata"
    ERROR = "error"