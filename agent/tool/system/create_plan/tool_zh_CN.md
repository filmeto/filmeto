---
name: create_plan
description: 为当前项目创建一个执行计划
parameters:
  - name: title
    description: 计划标题
    type: string
    required: true
    default: 未命名计划
  - name: description
    description: 计划描述
    type: string
    required: false
    default: 未提供描述
  - name: tasks
    description: 任务列表，每个任务包含 id、name、description、title、parameters、needs 等字段
    type: array
    required: true
    default: []
return_description: 返回创建的计划详情，包括计划 ID、标题、描述、任务列表、创建时间和状态
---
