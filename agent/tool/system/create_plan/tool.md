---
name: create_plan
description:
  en_US: Create a plan execution for the current project
  zh_CN: 为当前项目创建一个执行计划
parameters:
  - name: title
    description:
      en_US: Plan title
      zh_CN: 计划标题
    type: string
    required: true
    default: Untitled Plan
  - name: description
    description:
      en_US: Plan description
      zh_CN: 计划描述
    type: string
    required: false
    default: No description provided
  - name: tasks
    description:
      en_US: List of tasks, each task contains fields like id, name, description, title, parameters, needs
      zh_CN: 任务列表，每个任务包含 id、name、description、title、parameters、needs 等字段
    type: array
    required: true
    default: []
return_description:
  en_US: Returns the created plan details including plan ID, title, description, task list, creation time, and status
  zh_CN: 返回创建的计划详情，包括计划 ID、标题、描述、任务列表、创建时间和状态
---
