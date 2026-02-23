---
name: plan
description: "管理项目中的计划 - 创建、删除、更新、获取和列出计划"
parameters:
  - name: operation
    description: "操作类型：create（创建）、delete（删除）、update（更新）、get（获取）、list（列出所有）"
    type: string
    required: true
  - name: plan_id
    description: "计划 ID。用于 delete、update 和 get 操作"
    type: string
    required: false
  - name: title
    description: "计划标题。用于 create 和 update 操作"
    type: string
    required: false
  - name: description
    description: "计划描述。用于 create 和 update 操作"
    type: string
    required: false
  - name: tasks
    description: "任务列表，每个任务包含 id、name、description、title、parameters、needs 等字段。用于 create 和 update 操作"
    type: array
    required: false
  - name: append_tasks
    description: "要追加到计划的其他任务。用于 update 操作"
    type: array
    required: false
return_description: 返回操作结果，包含成功状态、操作详情和计划信息
---
