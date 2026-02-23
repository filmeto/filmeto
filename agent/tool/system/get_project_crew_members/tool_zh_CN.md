---
name: get_project_crew_members
description: 获取当前项目中的团队成员列表
parameters:
  - name: project
    description: 项目对象，包含项目名称等信息
    type: object
    required: false
    default: null
return_description: 返回团队成员列表，每个成员包含 id、name、role、description、soul、skills、model、temperature、max_steps、color 和 icon 等信息
---
