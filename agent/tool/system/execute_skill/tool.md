---
name: execute_skill
description:
  en_US: Execute a skill through ReAct-based chat stream
  zh_CN: 通过 ReAct 执行一个 skill
parameters:
  - name: skill_name
    description:
      en_US: Name of the skill to execute
      zh_CN: skill 名称
    type: string
    required: true
  - name: prompt
    description:
      en_US: Task prompt including required details
      zh_CN: 任务描述/提示词（包含执行所需的关键信息）
    type: string
    required: true
return_description:
  en_US: Returns the execution result from the skill (streamed)
  zh_CN: 返回 skill 的执行结果（流式输出）
---
