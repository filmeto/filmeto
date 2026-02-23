---
name: video_timeline
description:
  en_US: Manage video timeline items - add, delete, move, and update timeline cards. Timeline indices are 1-indexed.
  zh_CN: 管理视频时间线项目 - 增加、删除、移动和更新时间线卡片。时间线索引从 1 开始。
parameters:
  - name: operation
    description:
      en_US: Operation type: add, delete, move, update, list, or get
      zh_CN: 操作类型：add（增加）、delete（删除）、move（移动）、update（更新）、list（列出所有时间线项目）、get（获取单个时间线项目）
    type: string
    required: true
  - name: index
    description:
      en_US: Timeline item index (1-indexed). Required for delete, move, update, get operations
      zh_CN: 时间线项目的索引（从 1 开始）。用于 delete、move、update、get 操作
    type: number
    required: false
  - name: to_index
    description:
      en_US: Target position index (1-indexed). Required for move operation
      zh_CN: 目标位置索引（从 1 开始）。仅用于 move 操作
    type: number
    required: false
  - name: image_path
    description:
      en_US: Path to image file. Used for update operation
      zh_CN: 图片文件路径。仅用于 update 操作
    type: string
    required: false
  - name: video_path
    description:
      en_US: Path to video file. Used for update operation
      zh_CN: 视频文件路径。仅用于 update 操作
    type: string
    required: false
return_description:
  en_US: Returns operation result with success status, operation details, and current timeline info
  zh_CN: 返回操作结果，包含成功状态、操作详情和当前时间线信息
---
