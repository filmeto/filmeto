---
name: production_plan
description: 通过分析剧组能力、分解任务和调度剧组人员分配来创建完整的电影制作规划。调用此技能时，必须在 prompt 中包含完整的团队成员信息（包括每个成员的姓名、职位、描述和技能），以便直接进行任务分配，避免额外的信息查询。
tools:
  - plan
---
# 电影制作规划创建

## 关键要求：多步骤执行

此技能需要**按顺序进行多个工具调用**。在提供最终响应之前，您必须完成所有步骤。

**强制执行检查清单** - 在完成所有步骤之前不得结束：
- [ ] 第一步：验证 prompt 中是否包含团队成员信息
- [ ] 第二步：分析团队信息和用户需求
- [ ] 第三步：调用 `plan` 工具，使用 `create` 操作存储制作规划

**完成标准**：此任务仅在以下情况才算完成：
- 您已成功调用 `plan` 工具的 `create` 操作
- 规划已成功创建（您收到了包含 plan_id 的成功响应）
- 您已提供所创建规划的摘要

---

## 调用方须知：prompt 参数要求

**重要**：调用此技能时，`prompt` 参数**必须包含**团队成员的完整信息。请在 prompt 中明确列出：

```
## 团队成员信息
- **成员姓名** (role: 职位)
  - Description: 成员描述
  - Skills: 技能1, 技能2

例如：
- **黄小新** (role: screenwriter)
  - Description: 负责剧本全局规划、故事结构设计、角色塑造和对话创作
  - Skills: script_writing, character_development, dialogue_writing
- **李明** (role: director)
  - Description: 负责创意愿景、演员指导、场景设计
  - Skills: scene_breakdown, shot_planning, actor_direction
```

**正确的 execute_skill 调用示例：**
```json
{
  "skill_name": "production_plan",
  "prompt": "用户需求：重写剧本。\n\n## 团队成员信息\n- **黄小新** (role: screenwriter)\n  - Description: 负责剧本全局规划、故事结构设计、角色塑造和对话创作\n  - Skills: script_writing, character_development, dialogue_writing\n- **李明** (role: director)\n  - Description: 负责创意愿景、演员指导、场景设计\n  - Skills: scene_breakdown, shot_planning, actor_direction\n\n请根据以上团队成员创建剧本重写计划。"
}
```

---

## 第一步：验证团队成员信息

检查 prompt 中是否已包含团队成员信息。

**如果 prompt 中包含团队成员信息**：直接使用这些信息进行任务分配。

**如果 prompt 中缺少团队成员信息**：使用默认的通用职位进行任务分配，包括：
- `producer` - 制片人
- `director` - 导演
- `screenwriter` - 编剧
- `cinematographer` - 摄影指导
- `editor` - 剪辑师
- `sound_designer` - 音效设计师
- `vfx_supervisor` - 视觉特效总监
- `storyboard_artist` - 故事板艺术家

---

## 第二步：分析和分解任务

分析用户的制作需求：
- 将整体制作目标分解为具体的、可执行的任务
- 识别任务依赖关系（哪些任务必须先完成才能开始其他任务）
- 根据职位和技能将每个任务匹配到最合适的团队成员

---

## 第三步：创建并存储制作规划

最后，使用 `plan` 工具的 `create` 操作来存储制作规划：
- 根据制作目标给规划起一个描述性的标题
- 编写清晰的描述，说明规划涵盖的内容
- 包含所有任务，并正确填写：
  - `id`：唯一的任务标识符（例如 "task_1", "task_2"）
  - `name`：简短的任务名称
  - `description`：详细的任务描述
  - `title`：负责的剧组成员职位（例如 producer、director、screenwriter）
  - `needs`：此任务依赖的任务 ID 列表
  - `parameters`：其他任务参数（可以为空 {}）

**工具调用示例：**
```json
{
  "type": "tool",
  "tool_name": "plan",
  "tool_args": {
    "operation": "create",
    "title": "前期制作日程",
    "description": "电影项目的完整前期制作工作流程",
    "tasks": [
      {
        "id": "task_1",
        "name": "剧本开发",
        "description": "开发完整剧本",
        "title": "screenwriter",
        "needs": []
      }
    ]
  }
}
```

---

## 有效的剧组职位

分配任务时，仅使用以下有效的剧组职位：
- `producer` - 制片人（制作管理、调度、预算）
- `director` - 导演（创意愿景、选角、勘景）
- `screenwriter` - 编剧（剧本开发、对白）
- `cinematographer` - 摄影指导（视觉风格、摄影工作）
- `editor` - 剪辑师（后期制作、节奏、叙事流程）
- `sound_designer` - 音效设计师（音频、音乐、音效）
- `vfx_supervisor` - 视觉特效总监（视觉特效、CGI）
- `storyboard_artist` - 故事板艺术家（视觉规划、镜头列表）

---

## 任务依赖关系

使用 `needs` 字段指定依赖关系。例如：
```json
{
  "id": "task_2",
  "name": "勘景",
  "title": "director",
  "needs": ["task_1"]
}
```
这表示 task_2 必须等 task_1 完成后才能开始。

---

## 规划命名

选择清晰、描述性的规划标题，例如：
- "前期制作日程"
- "主体拍摄计划"
- "后期制作工作流程"
- "完整电影制作流程"

---

## 完整示例

以下是完整的前期制作规划示例：

```json
{
  "operation": "create",
  "title": "前期制作日程",
  "description": "从剧本开发到拍摄前准备的完整前期制作工作流程",
  "tasks": [
    {
      "id": "task_1",
      "name": "剧本开发",
      "description": "开发包含对白和场景描述的完整剧本",
      "title": "screenwriter",
      "needs": []
    },
    {
      "id": "task_2",
      "name": "故事板创作",
      "description": "根据最终剧本创建视觉故事板",
      "title": "storyboard_artist",
      "needs": ["task_1"]
    },
    {
      "id": "task_3",
      "name": "勘景",
      "description": "寻找并确定符合场景要求的拍摄地点",
      "title": "director",
      "needs": ["task_1"]
    },
    {
      "id": "task_4",
      "name": "选角",
      "description": "举行试镜并为所有角色选择演员",
      "title": "director",
      "needs": ["task_1"]
    },
    {
      "id": "task_5",
      "name": "制作预算",
      "description": "创建涵盖所有制作费用的详细预算",
      "title": "producer",
      "needs": ["task_1"]
    },
    {
      "id": "task_6",
      "name": "拍摄日程",
      "description": "根据地点和演员可用性创建详细的拍摄日程",
      "title": "producer",
      "needs": ["task_2", "task_3", "task_4", "task_5"]
    }
  ]
}
```

---

## 请记住

1. **验证** prompt 中是否包含团队成员信息
2. 使用提供的团队成员信息或默认使用通用职位
3. 根据团队能力分析和规划任务
4. **必须**以 `plan` 的 `create` 操作结束
5. 仅在规划成功创建后才提供最终摘要
