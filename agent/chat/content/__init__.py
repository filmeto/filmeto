"""
Content package for Filmeto agent system.
Defines all structured content types for messages.
"""
from typing import Dict, Type

from agent.chat.agent_chat_types import ContentType

from .content_status import ContentStatus
from .structure_content import StructureContent
from .text_content import TextContent
from .thinking_content import ThinkingContent
from .tool_content import ToolCallContent, ToolResponseContent
from .progress_content import ProgressContent
from .code_content import CodeBlockContent
from .media_content import ImageContent, VideoContent, AudioContent
from .metadata_content import MetadataContent
from .error_content import ErrorContent
from .file_content import FileAttachmentContent
from .data_content import TableContent, ChartContent
from .link_content import LinkContent
from .button_content import ButtonContent
from .form_content import FormContent
from .skill_content import SkillContent
from .plan_content import PlanContent, StepContent, TaskListContent


# Mapping of ContentType to appropriate subclass
_CONTENT_CLASS_MAP: Dict[ContentType, type] = {
    ContentType.TEXT: TextContent,
    ContentType.THINKING: ThinkingContent,
    ContentType.TOOL_CALL: ToolCallContent,
    ContentType.TOOL_RESPONSE: ToolResponseContent,
    ContentType.PROGRESS: ProgressContent,
    ContentType.CODE_BLOCK: CodeBlockContent,
    ContentType.IMAGE: ImageContent,
    ContentType.VIDEO: VideoContent,
    ContentType.AUDIO: AudioContent,
    ContentType.TABLE: TableContent,
    ContentType.CHART: ChartContent,
    ContentType.LINK: LinkContent,
    ContentType.BUTTON: ButtonContent,
    ContentType.FORM: FormContent,
    ContentType.METADATA: MetadataContent,
    ContentType.ERROR: ErrorContent,
    ContentType.FILE_ATTACHMENT: FileAttachmentContent,
    ContentType.SKILL: SkillContent,
    ContentType.PLAN: PlanContent,
    ContentType.STEP: StepContent,
    ContentType.TASK_LIST: TaskListContent,
}


__all__ = [
    'ContentStatus',
    'StructureContent',
    'TextContent',
    'ThinkingContent',
    'ToolCallContent',
    'ToolResponseContent',
    'ProgressContent',
    'CodeBlockContent',
    'ImageContent',
    'VideoContent',
    'AudioContent',
    'TableContent',
    'ChartContent',
    'LinkContent',
    'ButtonContent',
    'FormContent',
    'MetadataContent',
    'ErrorContent',
    'FileAttachmentContent',
    'SkillContent',
    'PlanContent',
    'StepContent',
    'TaskListContent',
    'create_content',
]


def create_content(content_type: ContentType, **kwargs) -> StructureContent:
    """
    Factory function to create appropriate StructureContent subclass.

    Args:
        content_type: Type of content to create
        **kwargs: Arguments to pass to the content class constructor

    Returns:
        Appropriate StructureContent subclass instance
    """
    content_class = _CONTENT_CLASS_MAP.get(content_type, StructureContent)
    return content_class(content_type=content_type, **kwargs)
