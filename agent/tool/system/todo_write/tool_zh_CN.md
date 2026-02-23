---
name: todo_write
description: "为你当前的编码会话创建和管理结构化的任务列表。此工具帮助 AI 助手跟踪进度并组织复杂的任务。重要约束：1) TODO计划必须基于当前可用的工具来规划执行步骤；2) 不要将todo_write工具本身纳入TODO列表中。"
parameters:
  - name: todos
    description: "待办事项列表，每个项目包含 content（任务描述）、status（状态：pending/in_progress/completed）、activeForm（进行时形式）。注意：请根据当前可用工具来规划任务，不要包含使用todo_write本身作为任务。"
    type: array
    required: true
return_description: 返回任务列表的更新状态
---
