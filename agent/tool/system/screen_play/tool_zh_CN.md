---
name: screen_play
description: "管理剧本场景 - 创建、读取、更新、删除和查询场景"
parameters:
  - name: operation
    description: "操作类型：create（创建）、get（获取）、update（更新）、delete（删除）、list（列出所有）、get_by_title（按标题查找）、get_by_character（按角色查找）、get_by_location（按地点查找）"
    type: string
    required: true
  - name: scene_id
    description: 场景的唯一标识符。用于 create、get、update、delete 操作
    type: string
    required: false
  - name: title
    description: 场景标题。用于 create、update、get_by_title 操作
    type: string
    required: false
  - name: content
    description: 场景内容，使用 Markdown 格式。用于 create、update 操作
    type: string
    required: false
  - name: metadata
    description: 场景元数据字典。包含 scene_number（场景编号）、location（地点）、time_of_day（时间）、genre（类型）、logline（故事梗概）、characters（角色列表）、story_beat（故事节拍）、page_count（页数）、duration_minutes（时长）、tags（标签）、status（状态）、revision_number（修订号）。用于 create、update 操作
    type: object
    required: false
  - name: character_name
    description: 要搜索的角色名称。用于 get_by_character 操作
    type: string
    required: false
  - name: location
    description: 要搜索的地点（支持部分匹配）。用于 get_by_location 操作
    type: string
    required: false
return_description: 返回操作结果，包含成功状态、场景详情和摘要信息
---
