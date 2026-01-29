# AgentEventType, ContentType, MessageType 分析与改进建议

## 一、当前定义总结

### 1. AgentEventType (13个)
```python
LLM_THINKING       # LLM思考过程
TOOL_START         # 工具开始执行
TOOL_PROGRESS      # 工具执行进度
TOOL_END           # 工具执行结束
LLM_OUTPUT         # LLM原始输出
FINAL              # 最终响应
ERROR              # 错误
USER_MESSAGE       # 用户消息
PAUSE              # 暂停
RESUME             # 恢复
STATUS_CHANGE      # 状态变更
TODO_UPDATE        # TODO更新
```

### 2. ContentType (17个)
```python
TEXT              # ✓ TextContent
CODE_BLOCK        # ✓ CodeBlockContent
IMAGE             # ✓ ImageContent
VIDEO             # ✓ VideoContent
AUDIO             # ✗ 未实现
FILE_ATTACHMENT   # ✓ FileAttachmentContent
TABLE             # ✗ 未实现
CHART             # ✗ 未实现
LINK              # ✗ 未实现
BUTTON            # ✗ 未实现
FORM              # ✗ 未实现
PROGRESS          # ✓ ProgressContent
METADATA          # ✓ MetadataContent
SKILL             # ✗ 未实现
THINKING          # ✓ ThinkingContent
TOOL_CALL         # ✓ ToolCallContent
TOOL_RESPONSE     # ✓ ToolResponseContent
ERROR             # ✓ ErrorContent
```

### 3. MessageType (12个)
```python
TEXT            # 文本消息
CODE            # 代码消息
IMAGE           # 图片消息
VIDEO           # 视频消息
AUDIO           # 音频消息
FILE            # 文件消息
COMMAND         # 命令消息
ERROR           # 错误消息
SYSTEM          # 系统消息
THINKING        # 思考消息
TOOL_CALL       # 工具调用消息
TOOL_RESPONSE   # 工具响应消息
```

## 二、按三大原则分析

### 原则1：AgentEventType应表达大模型群聊过程中的各种处理环节

#### ✅ 已覆盖的环节：
- LLM思考过程：`LLM_THINKING`
- LLM原始输出：`LLM_OUTPUT`
- 工具调用全流程：`TOOL_START`, `TOOL_PROGRESS`, `TOOL_END`
- 用户交互：`USER_MESSAGE`
- 终止状态：`FINAL`, `ERROR`
- 控制流：`PAUSE`, `RESUME`
- 元状态：`STATUS_CHANGE`, `TODO_UPDATE`

#### ❌ 缺失的关键环节：

**1. Crew成员层面（CrewMember）**
```python
# 缺失
CREW_MEMBER_START      # Crew成员开始处理任务
CREW_MEMBER_THINKING   # Crew成员的思考（区别于LLM思考）
CREW_MEMBER_END        # Crew成员完成处理
```

**2. Skill执行层面（SkillService）**
```python
# 缺失
SKILL_START           # Skill开始执行
SKILL_PROGRESS        # Skill执行进度
SKILL_END             # Skill执行完成
SKILL_ERROR           # Skill执行错误
```

**3. 计划层面（PlanService）**
```python
# 缺失
PLAN_CREATED          # 计划创建完成
PLAN_UPDATED          # 计划更新
PLAN_STEP_START       # 计划步骤开始
PLAN_STEP_END         # 计划步骤完成
PLAN_STEP_FAILED      # 计划步骤失败
```

**4. 流程控制层面**
```python
# 已有但不够细化
STEP_START            # 当前步骤开始（已有STATUS_CHANGE可以表达，但不明确）
STEP_END              # 当前步骤结束
INTERRUPTED           # 用户中断
TIMEOUT               # 超时
```

#### 🔧 改进建议：

**建议1：添加Crew成员事件**
```python
class AgentEventType(str, Enum):
    # ... 现有类型 ...

    # Crew成员事件
    CREW_MEMBER_START = "crew_member_start"       # Crew成员开始处理
    CREW_MEMBER_THINKING = "crew_member_thinking" # Crew成员思考
    CREW_MEMBER_END = "crew_member_end"           # Crew成员完成
```

**建议2：添加Skill执行事件**
```python
class AgentEventType(str, Enum):
    # ... 现有类型 ...

    # Skill执行事件
    SKILL_START = "skill_start"                   # Skill开始
    SKILL_PROGRESS = "skill_progress"             # Skill进度
    SKILL_END = "skill_end"                       # Skill完成
    SKILL_ERROR = "skill_error"                   # Skill错误
```

**建议3：添加计划相关事件**
```python
class AgentEventType(str, Enum):
    # ... 现有类型 ...

    # 计划相关事件
    PLAN_CREATED = "plan_created"                 # 计划创建
    PLAN_UPDATED = "plan_updated"                 # 计划更新
    PLAN_STEP_START = "plan_step_start"           # 步骤开始
    PLAN_STEP_END = "plan_step_end"               # 步骤完成
    PLAN_STEP_FAILED = "plan_step_failed"         # 步骤失败
```

### 原则2：StructureContent应表达各环节的输出内容和状态

#### ✅ 已实现的内容类型（11个）：
- 基础内容：TextContent, CodeBlockContent
- 思考过程：ThinkingContent
- 工具相关：ToolCallContent, ToolResponseContent
- 进度状态：ProgressContent
- 多媒体：ImageContent, VideoContent
- 元数据：MetadataContent
- 错误：ErrorContent
- 附件：FileAttachmentContent

#### ❌ ContentType定义但未实现的（7个）：

**1. AUDIO - 音频内容**
```python
# 建议实现
@dataclass
class AudioContent(StructureContent):
    """音频内容。"""
    content_type: ContentType = ContentType.AUDIO
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # 秒
    transcript: Optional[str] = None  # 转录文本
```

**2. TABLE - 表格内容**
```python
# 建议实现
@dataclass
class TableContent(StructureContent):
    """表格内容。"""
    content_type: ContentType = ContentType.TABLE
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    title: Optional[str] = None
```

**3. CHART - 图表内容**
```python
# 建议实现
@dataclass
class ChartContent(StructureContent):
    """图表内容。"""
    content_type: ContentType = ContentType.CHART
    chart_type: str = ""  # bar, line, pie, etc.
    data: Dict[str, Any] = field(default_factory=dict)
    title: Optional[str] = None
```

**4. LINK - 链接内容**
```python
# 建议实现
@dataclass
class LinkContent(StructureContent):
    """链接内容。"""
    content_type: ContentType = ContentType.LINK
    url: str = ""
    title: Optional[str] = None
    description: Optional[str] = None
    favicon_url: Optional[str] = None
```

**5. BUTTON - 按钮内容（交互元素）**
```python
# 建议实现
@dataclass
class ButtonContent(StructureContent):
    """按钮内容（交互元素）。"""
    content_type: ContentType = ContentType.BUTTON
    label: str = ""
    action: str = ""  # 点击后的动作
    style: str = "primary"  # primary, secondary, danger, etc.
    disabled: bool = False
```

**6. FORM - 表单内容（交互元素）**
```python
# 建议实现
@dataclass
class FormContent(StructureContent):
    """表单内容（交互元素）。"""
    content_type: ContentType = ContentType.FORM
    fields: List[Dict[str, Any]] = field(default_factory=list)
    submit_action: str = ""
    title: Optional[str] = None
```

**7. SKILL - 技能信息内容**
```python
# 建议实现
@dataclass
class SkillContent(StructureContent):
    """技能信息内容。"""
    content_type: ContentType = ContentType.SKILL
    skill_name: str = ""
    skill_description: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    example_call: Optional[str] = None
```

#### ❌ 完全缺失的内容类型：

**1. 计划相关内容**
```python
# 建议添加到ContentType和实现
PLAN = "plan"  # 计划内容

@dataclass
class PlanContent(StructureContent):
    """计划内容。"""
    content_type: ContentType = ContentType.PLAN
    plan_id: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed
```

**2. 步骤相关内容**
```python
# 建议添加到ContentType和实现
STEP = "step"  # 步骤内容

@dataclass
class StepContent(StructureContent):
    """步骤内容。"""
    content_type: ContentType = ContentType.STEP
    step_id: str = ""
    step_number: int = 0
    description: str = ""
    status: str = "pending"
    result: Optional[Any] = None
```

**3. 任务列表相关内容**
```python
# 建议添加到ContentType和实现
TASK_LIST = "task_list"  # 任务列表

@dataclass
class TaskListContent(StructureContent):
    """任务列表内容。"""
    content_type: ContentType = ContentType.TASK_LIST
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    completed_count: int = 0
    total_count: int = 0
```

### 原则3：AgentChatMessage应表达群聊卡片信息

#### ✅ 当前MessageType基本合理，但问题分析：

**问题1：MessageType和ContentType职责不清**

- `MessageType.TEXT` vs `ContentType.TEXT` - 混淆
- `MessageType.CODE` vs `ContentType.CODE_BLOCK` - 不一致
- `MessageType.IMAGE` vs `ContentType.IMAGE` - 重复

**问题2：MessageType不应该包含具体内容类型**

- MessageType应该表达"消息的类别/用途"，而不是"内容的形式"
- 例如：`THINKING`, `TOOL_CALL`, `TOOL_RESPONSE` 应该是事件类型，不应该是消息类型

#### 🔧 改进建议：

**建议1：重新定义MessageType的职责**
```python
class MessageType(Enum):
    """消息类型 - 表达消息的用途和角色"""
    USER = "user"                 # 用户消息
    ASSISTANT = "assistant"       # 助手消息
    SYSTEM = "system"             # 系统消息
    NOTIFICATION = "notification"  # 通知消息

    # 或者按照消息的功能分类
    CHAT = "chat"                 # 聊天消息
    STATUS = "status"             # 状态消息
    CONTROL = "control"           # 控制消息（命令）
    ALERT = "alert"               # 警告消息
```

**建议2：Message通过structured_content列表来表达内容**
```python
@dataclass
class AgentMessage:
    """群聊卡片信息"""
    message_type: MessageType  # 消息的用途/角色
    sender_id: str
    sender_name: str
    structured_content: List[StructureContent]  # 内容通过StructureContent表达
```

## 三、完整的类型定义建议

### 改进后的AgentEventType

```python
class AgentEventType(str, Enum):
    """大模型群聊过程中的各种处理环节事件"""

    # === LLM相关 ===
    LLM_THINKING = "llm_thinking"       # LLM思考中
    LLM_OUTPUT = "llm_output"           # LLM原始输出

    # === Crew成员相关 ===
    CREW_MEMBER_START = "crew_member_start"       # Crew成员开始处理
    CREW_MEMBER_THINKING = "crew_member_thinking" # Crew成员思考
    CREW_MEMBER_END = "crew_member_end"           # Crew成员完成

    # === Skill相关 ===
    SKILL_START = "skill_start"         # Skill开始
    SKILL_PROGRESS = "skill_progress"   # Skill进度
    SKILL_END = "skill_end"             # Skill完成
    SKILL_ERROR = "skill_error"         # Skill错误

    # === 工具相关 ===
    TOOL_START = "tool_start"           # 工具开始
    TOOL_PROGRESS = "tool_progress"     # 工具进度
    TOOL_END = "tool_end"               # 工具完成

    # === 计划相关 ===
    PLAN_CREATED = "plan_created"       # 计划创建
    PLAN_UPDATED = "plan_updated"       # 计划更新
    PLAN_STEP_START = "plan_step_start" # 步骤开始
    PLAN_STEP_END = "plan_step_end"     # 步骤完成
    PLAN_STEP_FAILED = "plan_step_failed" # 步骤失败

    # === 状态相关 ===
    STEP_START = "step_start"           # 当前步骤开始
    STEP_END = "step_end"               # 当前步骤结束
    STATUS_CHANGE = "status_change"     # 状态变更
    TODO_UPDATE = "todo_update"         # TODO更新

    # === 终止相关 ===
    FINAL = "final"                     # 最终响应
    ERROR = "error"                     # 错误
    INTERRUPTED = "interrupted"         # 用户中断
    TIMEOUT = "timeout"                 # 超时

    # === 控制相关 ===
    USER_MESSAGE = "user_message"       # 用户消息
    PAUSE = "pause"                     # 暂停
    RESUME = "resume"                   # 恢复
```

### 改进后的ContentType

```python
class ContentType(Enum):
    """内容类型 - 表达各种产出物的形式"""

    # === 基础内容 ===
    TEXT = "text"                       # 纯文本
    CODE_BLOCK = "code_block"           # 代码块

    # === 思考内容 ===
    THINKING = "thinking"               # 思考过程

    # === 工具内容 ===
    TOOL_CALL = "tool_call"             # 工具调用
    TOOL_RESPONSE = "tool_response"     # 工具响应

    # === 多媒体内容 ===
    IMAGE = "image"                     # 图片
    VIDEO = "video"                     # 视频
    AUDIO = "audio"                     # 音频

    # === 数据展示 ===
    TABLE = "table"                     # 表格
    CHART = "chart"                     # 图表

    # === 交互元素 ===
    LINK = "link"                       # 链接
    BUTTON = "button"                   # 按钮
    FORM = "form"                       # 表单

    # === 文件相关 ===
    FILE_ATTACHMENT = "file_attachment" # 文件附件

    # === 任务和计划 ===
    PLAN = "plan"                       # 计划
    STEP = "step"                       # 步骤
    TASK_LIST = "task_list"             # 任务列表
    SKILL = "skill"                     # 技能信息

    # === 状态和元数据 ===
    PROGRESS = "progress"               # 进度
    METADATA = "metadata"               # 元数据
    ERROR = "error"                     # 错误
```

### 改进后的MessageType

```python
class MessageType(Enum):
    """消息类型 - 表达消息的用途和角色"""

    # === 按发送者分类 ===
    USER = "user"                       # 用户发送的消息
    ASSISTANT = "assistant"             # 助手发送的消息
    SYSTEM = "system"                   # 系统消息

    # === 按功能分类 ===
    CHAT = "chat"                       # 聊天消息
    STATUS = "status"                   # 状态更新消息
    CONTROL = "control"                 # 控制命令消息
    NOTIFICATION = "notification"       # 通知消息
    ALERT = "alert"                     # 警告/错误消息
```

## 四、实施建议

### 阶段1：补充缺失的StructureContent类
1. 实现AudioContent
2. 实现TableContent
3. 实现ChartContent
4. 实现LinkContent
5. 实现ButtonContent
6. 实现FormContent
7. 实现SkillContent
8. 新增PlanContent
9. 新增StepContent
10. 新增TaskListContent

### 阶段2：扩展AgentEventType
1. 添加Crew成员相关事件
2. 添加Skill执行相关事件
3. 添加计划相关事件

### 阶段3：重构MessageType
1. 明确MessageType的职责
2. 更新AgentMessage使用新的MessageType定义
3. 确保消息内容通过StructureContent表达

### 阶段4：更新文档和示例
1. 更新事件类型文档
2. 添加各种内容类型的使用示例
3. 提供最佳实践指南

## 五、总结

### 当前问题：
1. ✅ **AgentEventType**：基本合理，但缺少Crew、Skill、Plan层面的事件
2. ⚠️ **ContentType**：定义了17种，但只实现了11种，缺少计划/步骤相关类型
3. ❌ **MessageType**：职责不清，与ContentType混淆，需要重新定义

### 优先级：
1. **高优先级**：补充缺失的StructureContent类（影响功能完整性）
2. **中优先级**：扩展AgentEventType（增强事件追踪能力）
3. **低优先级**：重构MessageType（需要较大改动，但不影响现有功能）
