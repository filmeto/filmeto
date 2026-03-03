"""
Common enums for the agent module.
"""
from enum import Enum


class DisplayCategory(Enum):
    """
    Display category for content types.

    Used to determine how content should be displayed in the UI:
    - MAIN: Content displayed in the main content section (flat display)
    - AUXILIARY: Content displayed in thinking/collapsible section
    """
    MAIN = "main"
    AUXILIARY = "auxiliary"


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
    PLAN_TASK = "plan_task"  # PlanTask状态更新
    STEP = "step"
    TASK_LIST = "task_list"
    SKILL = "skill"

    # === 状态和元数据 ===
    PROGRESS = "progress"
    TYPING = "typing"
    METADATA = "metadata"
    ERROR = "error"
    LLM_OUTPUT = "llm_output"
    TODO_WRITE = "todo_write"  # TODO列表写入/更新

    def get_display_category(self) -> DisplayCategory:
        """
        Get the display category for this content type.

        Returns:
            DisplayCategory: MAIN for content shown in main section,
                           AUXILIARY for content shown in thinking section

        Main content types (flat display):
        - text, code_block, image, video, audio, link, button, form, file_attachment

        Auxiliary content types (collapsible thinking section):
        - thinking, tool_call, tool_response, skill, plan, plan_task, step,
          progress, metadata, error, llm_output, todo_write, typing, table, chart
        """
        # Main content types - displayed in the main content section
        main_types = {
            ContentType.TEXT,
            ContentType.CODE_BLOCK,
            ContentType.IMAGE,
            ContentType.VIDEO,
            ContentType.AUDIO,
            ContentType.LINK,
            ContentType.BUTTON,
            ContentType.FORM,
            ContentType.FILE_ATTACHMENT,
        }

        if self in main_types:
            return DisplayCategory.MAIN
        else:
            return DisplayCategory.AUXILIARY

    def is_main_content(self) -> bool:
        """Check if this content type should be displayed in the main section."""
        return self.get_display_category() == DisplayCategory.MAIN

    def is_auxiliary_content(self) -> bool:
        """Check if this content type should be displayed in the thinking section."""
        return self.get_display_category() == DisplayCategory.AUXILIARY