---
name: story_board
description: "管理分镜镜头，支持增删改查以及文生图/图生图关键帧生成"
parameters:
  - name: operation
    description: "操作类型：create、get、update、delete、delete_batch、delete_all、list、text2image、image2image"
    type: string
    required: true
  - name: scene_id
    description: "镜头所属场景 ID"
    type: string
    required: false
  - name: shot_id
    description: "场景下镜头 ID；用于 get/update/delete/text2image/image2image。create 不传则自动生成"
    type: string
    required: false
  - name: shot_ids
    description: "delete_batch 使用的镜头 ID 列表"
    type: array
    required: false
  - name: description
    description: "镜头文字描述（作为 shot.md 正文存储）"
    type: string
    required: false
  - name: keyframe_context
    description: "关键帧辅助元数据（prompt/model/reference/tool）"
    type: object
    required: false
  - name: prompt
    description: "文生图/图生图的提示词"
    type: string
    required: false
  - name: input_image_path
    description: "图生图输入图片路径；为空时会尝试使用当前镜头已有关键帧"
    type: string
    required: false
  - name: reference_images
    description: "文生图参考图路径列表"
    type: array
    required: false
  - name: width
    description: "生成图宽度"
    type: number
    required: false
    default: 1024
  - name: height
    description: "生成图高度"
    type: number
    required: false
    default: 1024
  - name: server_name
    description: "可选：指定生成服务名"
    type: string
    required: false
  - name: model
    description: "可选：指定生成模型名"
    type: string
    required: false
return_description: "返回操作结果，包含镜头详情、CRUD 状态或生成后的关键帧路径"
---
