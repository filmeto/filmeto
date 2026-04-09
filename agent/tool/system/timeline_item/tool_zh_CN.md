---
name: timeline_item
description: "创建或编辑时间线卡片，保持与界面一致的选中/刷新行为，并可基于 prompt + ability 提交图片/视频/音频生成任务。"
parameters:
  - name: operation
    description: "操作类型：upsert、create 或 edit"
    type: string
    required: false
    default: upsert
  - name: index
    description: "目标时间线索引（从 1 开始）。upsert/create 可不传。"
    type: number
    required: false
  - name: prompt
    description: "写入目标时间线 item 的提示词（当设置 ability 时按工具维度保存）。"
    type: string
    required: false
  - name: ability
    description: "生成能力/工具类型，例如 image/video/audio 或 text2image/text2video/text2music/text2speak。"
    type: string
    required: false
  - name: submit_task
    description: "是否立即提交该时间线 item 的生成任务。"
    type: boolean
    required: false
    default: false
  - name: selection_mode
    description: "可选，模型选择模式覆盖。"
    type: string
    required: false
  - name: server_name
    description: "可选，任务 server 覆盖。"
    type: string
    required: false
  - name: model_name
    description: "可选，任务 model 覆盖。"
    type: string
    required: false
  - name: selection_tags
    description: "可选，能力选择 tags。"
    type: array
    required: false
  - name: min_priority
    description: "可选，自动选择最小优先级。"
    type: number
    required: false
return_description: 返回选中的索引、是否新建、是否提交任务以及最终任务参数。
---
