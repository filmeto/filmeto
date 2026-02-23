---
name: create_execution_plan
description: 为影视制作项目创建执行计划，使用计划工具
tools:
  - plan
  - crew_member
---
# 执行计划创建技能

此技能使用计划工具为影视制作项目创建执行计划。它允许制片人和其他剧组人员定义和跟踪项目里程碑、任务和职责。

## 功能

- 创建具有命名任务和依赖关系的结构化执行计划
- 使用有效职位将任务分配给特定的剧组成员
- 定义任务参数和任务之间的依赖关系
- 跟踪项目里程碑和职责

## 计划创建的重要说明

创建计划时，您必须提供以下 JSON 格式的任务：

每个任务必须包含：id、name、description、title、needs、parameters。

职位必须是以下有效的剧组成员职位之一：
- producer（制片人）
- director（导演）
- screenwriter（编剧）
- cinematographer（摄影指导）
- editor（剪辑师）
- sound_designer（音效设计师）
- vfx_supervisor（视觉特效总监）
- storyboard_artist（故事板艺术家）

使用任何其他职位（如'system'、'user'、'assistant'等）将导致任务失败。

任务可以在'needs'字段中定义依赖关系，该字段应包含在此任务开始之前必须完成的其他任务ID的数组。

## 输入要求

通过 `execute_skill_script` 调用脚本时提供以下输入：

- `plan_name`（字符串，必需）：执行计划的名称。
- `description`（字符串，可选）：计划的描述。
- `tasks`（数组，可选）：计划的任务列表。如果未提供，则根据提示创建一个最小化的合理任务列表。
  - 每个任务应包含：`id`、`name`、`description`、`title`、`needs`、`parameters`。
  - `title` 必须是上面列出的有效剧组成员职位之一。

如果未明确提供 `plan_name`，请从提示中派生一个简洁的名称。

## 使用方法

当用户想要为影视制作项目创建结构化执行计划时，可以调用此技能。该计划将创建指定的任务并分配给适当的剧组成员。

## 执行上下文

此技能支持直接脚本执行和通过 SkillExecutor 进行上下文执行。当通过 SkillExecutor 执行时，它接收包含项目和 workspace 信息的 SkillContext 对象，参数直接传递给 execute 函数。

## 参数示例

```json
{
  "plan_name": "前期制作日程",
  "description": "前期制作活动的详细日程",
  "tasks": [
    {
      "id": "task1",
      "name": "剧本定稿",
      "description": "完成剧本的最终修订",
      "title": "screenwriter",
      "needs": [],
      "parameters": {}
    },
    {
      "id": "task2",
      "name": "勘景",
      "description": "寻找并确定拍摄地点",
      "title": "director",
      "needs": ["task1"],
      "parameters": {}
    },
    {
      "id": "task3",
      "name": "选角",
      "description": "举行试镜并选择演员",
      "title": "director",
      "needs": ["task1"],
      "parameters": {}
    }
  ]
}
```

## 输出

返回包含以下内容的 JSON 对象：
- `success`：指示操作是否成功的布尔值
- `message`：人类可读的状态消息
- `plan_id`：所创建计划的唯一标识符
- `plan_name`：所创建计划的名称
- `project`：计划所属的项目名称
