---
name: production_plan
description: 通过分析剧组能力、分解任务和调度剧组人员分配来创建完整的电影制作规划
tools:
  - crew_member
  - plan
---
# 电影制作规划创建

## 关键要求：多步骤执行

此技能需要**按顺序进行多个工具调用**。在提供最终响应之前，您必须完成所有步骤。

**强制执行检查清单** - 在完成所有步骤之前不得结束：
- [ ] 第一步：收集剧组成员信息（详见下方第一步说明）
- [ ] 第二步：分析剧组信息和用户需求
- [ ] 第三步：调用 `plan` 工具，使用 `create` 操作存储制作规划

**完成标准**：此任务仅在以下情况才算完成：
- 您已成功调用 `plan` 工具的 `create` 操作
- 规划已成功创建（您收到了包含 plan_id 的成功响应）
- 您已提供所创建规划的摘要

**切勿**在仅调用 `crew_member` 后停止。您必须继续调用 `plan` 工具。

---

## 第一步：收集剧组成员信息

**重要提示**：在调用 `crew_member` 工具之前，请先检查输入中是否已提供剧组成员信息。

### 选项 A：输入中已提供剧组成员信息

如果输入中已包含剧组成员信息（在 `crew_members` 参数中或提示上下文中），**请勿**调用 `crew_member` 工具，直接使用提供的信息。

查找剧组成员数据的位置：
- 输入中的 `crew_members` 参数
- 提示中的"团队上下文"或"团队成员"部分

已提供的剧组成员信息示例：
```
- **Alex Chen** (role: director)
  - Description: Responsible for creative vision...
  - Skills: scene_breakdown, shot_planning
- **Jordan Lee** (role: screenwriter)
  - Description: Develops screenplay...
  - Skills: script_writing, character_development
```

### 选项 B：输入中未提供剧组成员信息 - 调用 crew_member 工具

如果输入中**未**提供剧组成员信息，请使用 `crew_member` 工具的 `list` 操作来：
- 获取所有可用的剧组成员
- 了解每个成员的职位、技能和能力
- 确定哪个剧组成员最适合每种类型的任务

**工具调用示例：**
```json
{
  "type": "tool",
  "tool_name": "crew_member",
  "tool_args": {
    "operation": "list"
  }
}
```

---

## 第二步：分析和分解任务

收集剧组信息后（无论来自输入还是工具调用），分析用户的制作需求：
- 将整体制作目标分解为具体的、可执行的任务
- 识别任务依赖关系（哪些任务必须先完成才能开始其他任务）
- 根据职位和技能将每个任务匹配到最合适的剧组成员

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

1. **首先检查**输入中是否已提供剧组成员信息
2. 仅在信息未提供时才调用 `crew_member` 的 `list` 操作
3. 根据剧组能力分析和规划任务
4. **必须**以 `plan` 的 `create` 操作结束
5. 仅在规划成功创建后才提供最终摘要
