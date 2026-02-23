---
name: execute_skill
description: 通过 ReAct 执行一个 skill
parameters:
  - name: skill_name
    description: skill 名称
    type: string
    required: true
  - name: prompt
    description: 任务描述/提示词（包含执行所需的关键信息）
    type: string
    required: true
return_description: 返回 skill 的执行结果（流式输出）
---
