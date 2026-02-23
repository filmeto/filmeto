---
name: execute_skill_script
description: 执行 skill 中预定义的脚本。可以直接指定完整脚本路径，或使用 skill_path + script_name 的组合。
parameters:
  - name: script_path
    description: 脚本的完整路径（优先使用此参数）
    type: string
    required: false
  - name: skill_path
    description: skill 目录路径（当 script_path 未提供时使用）
    type: string
    required: false
  - name: script_name
    description: 要执行的脚本名称（当 script_path 未提供时使用）
    type: string
    required: false
  - name: args
    description: 传递给脚本的参数
    type: object
    required: false
    default: {}
return_description: 返回脚本的执行结果（流式输出）
---
