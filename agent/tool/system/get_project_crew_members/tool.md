---
name: get_project_crew_members
description:
  en_US: Get the list of crew members in the current project
  zh_CN: 获取当前项目中的团队成员列表
parameters:
  - name: project
    description:
      en_US: Project object containing project name and other information
      zh_CN: 项目对象，包含项目名称等信息
    type: object
    required: false
    default: null
return_description:
  en_US: Returns a list of crew members, each member contains id, name, role, description, soul, skills, model, temperature, max_steps, color, and icon
  zh_CN: 返回团队成员列表，每个成员包含 id、name、role、description、soul、skills、model、temperature、max_steps、color 和 icon 等信息
---
