---
name: crew_member
description: "管理项目中的剧组成员 - 创建、删除、更新、获取和列出剧组成员"
parameters:
  - name: operation
    description: "操作类型：create（创建）、delete（删除）、update（更新）、get（获取）、list（列出所有）"
    type: string
    required: true
  - name: name
    description: "剧组成员名称。用于 delete、update 和 get 操作"
    type: string
    required: false
  - name: data
    description: "剧组成员数据对象。用于 create 和 update 操作。包含字段：name（名称）、description（描述）、soul（灵魂）、skills（技能）、model（模型）、temperature（温度）、max_steps（最大步数）、color（颜色）、icon（图标）、crew_title（剧组职位）和 prompt（提示词）"
    type: object
    required: false
return_description: 返回操作结果，包含成功状态、操作详情和剧组成员信息
---
