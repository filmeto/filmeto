---
name: todo
description: "管理用于跟踪复杂任务进度的待办事项列表 - 创建、删除、更新、获取和列出项目"
parameters:
  - name: operation
    description: "操作类型：create（创建）、delete（删除）、update（更新）、get（获取）、list（列出所有）"
    type: string
    required: true
  - name: todos
    description: "用于 create 操作的待办事项数组，每个项目包含 content（任务描述）、status（状态：pending/in_progress/completed）和 activeForm（进行时形式）"
    type: array
    required: false
  - name: todo_id
    description: "用于 delete、update 和 get 操作的待办事项 ID"
    type: string
    required: false
  - name: title
    description: "用于 delete、update 和 get 操作的待办事项标题（作为 todo_id 的替代）"
    type: string
    required: false
  - name: content
    description: "用于 update 操作的新内容/描述"
    type: string
    required: false
  - name: status
    description: "用于 update 操作的新状态：pending（待处理）、in_progress（进行中）、completed（已完成）、failed（失败）或 blocked（阻塞）"
    type: string
    required: false
  - name: activeForm
    description: "用于 update 操作的新进行时形式"
    type: string
    required: false
return_description: 返回操作结果，包含成功状态、操作详情和待办事项列表信息
---
