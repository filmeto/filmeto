---
name: production_plan
description: 通过分析剧组能力、分解任务和调度剧组人员分配来创建完整的电影制作规划。调用此技能时，必须在 prompt 中包含完整的团队成员信息（包括每个成员的姓名、职位、描述和技能），以便直接进行任务分配，避免额外的信息查询。
tools:
  - speak_to
  - plan
---
# 电影制作规划创建

## 关键要求：先路由，仅在必要时创建规划

**重要**：在创建任何规划之前，您必须首先评估任务是否可以由**单个**剧组成员处理。许多任务不需要复杂的规划——它们只需要直接路由。

### 决策流程：
1. **单个剧组成员能否处理？** → 使用 `speak_to` 工具的 `specify` 模式
2. **是否需要多个剧组成员协作？** → 使用 `plan` 工具创建规划

---

## 第零步：关键 - 评估任务复杂度（必须首先执行）

**在任何其他步骤之前**，分析用户的请求：

### 单剧组成员任务（使用 `speak_to` → specify 模式）

单人可处理的任务示例：
- "写一段场景描述" → @screenwriter
- "为第5场戏创建故事板" → @storyboard_artist
- "设计开场镜头的灯光" → @cinematographer
- "剪辑这个序列" → @editor
- "为这个片段添加音效" → @sound_designer
- "审阅剧本" → @director
- "创建镜头列表" → @director
- 任何具有明确单一责任的任务

**如果任务可以由一个剧组成员处理：**

```json
{
  "type": "tool",
  "tool_name": "speak_to",
  "tool_args": {
    "mode": "specify",
    "target": "screenwriter",
    "message": "请为开场序列写一段场景描述。"
  }
}
```

**不要为单人任务创建规划。到此为止并响应。**

### 多剧组成员任务（使用 `plan` 工具）

需要协作的任务示例：
- "制作一部完整的短片" → 需要编剧 → 导演 → 摄影指导 → 剪辑师
- "从剧本到最终成片创建完整视频" → 多个阶段
- "开发和拍摄一支广告" → 需要协调
- "规划整个前期制作工作流程" → 任务之间存在依赖关系
- 任何一人的输出是另一人输入的任务

**只有当任务真正需要多个剧组成员协作且存在依赖关系时，才继续执行第一步到第三步。**

---

## 第一步：验证团队成员信息（仅适用于多剧组成员任务）

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

## 第二步：分析和分解任务（仅适用于多剧组成员任务）

分析用户的制作需求：
- 将整体制作目标分解为具体的、可执行的任务
- 识别任务依赖关系（哪些任务必须先完成才能开始其他任务）
- 根据职位和技能将每个任务匹配到最合适的团队成员

---

## 第三步：创建并存储制作规划（仅适用于多剧组成员任务）

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

## 完整示例

### 示例一：单剧组成员任务（常见）

**用户请求**："为第5场戏创建故事板"

**分析**：这是一个可以由故事板艺术家独立处理的单一任务。

**操作**：使用 `speak_to` 工具（不要创建规划）

```json
{
  "type": "tool",
  "tool_name": "speak_to",
  "tool_args": {
    "mode": "specify",
    "target": "storyboard_artist",
    "message": "请根据剧本为第5场戏创建故事板。"
  }
}
```

### 示例二：多剧组成员任务

**用户请求**："从概念到最终成片制作一部完整的短片"

**分析**：这需要多个剧组成员按顺序协作，且存在依赖关系。

**操作**：创建规划

```json
{
  "type": "tool",
  "tool_name": "plan",
  "tool_args": {
    "operation": "create",
    "title": "短片制作流程",
    "description": "从概念到最终交付的完整工作流程",
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
        "name": "镜头规划",
        "description": "规划摄影镜头和视觉方案",
        "title": "director",
        "needs": ["task_2"]
      },
      {
        "id": "task_4",
        "name": "主体拍摄",
        "description": "执行计划的镜头",
        "title": "cinematographer",
        "needs": ["task_3"]
      },
      {
        "id": "task_5",
        "name": "后期剪辑",
        "description": "将素材剪辑成最终成片",
        "title": "editor",
        "needs": ["task_4"]
      }
    ]
  }
}
```

---

## 请记住

1. **首先评估** - 单个剧组成员能否处理此任务？
2. **单一任务？** → 使用 `speak_to` 的 `specify` 模式
3. **多个任务且有依赖关系？** → 使用 `plan` 工具
4. 只在真正需要时创建规划
5. 大多数用户请求可以通过路由到单个剧组成员来处理
