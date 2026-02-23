---
name: execute_skill_script
description:
  en_US: Execute a pre-defined script from a skill. Can specify full script path directly, or use skill_path + script_name combination.
  zh_CN: 执行 skill 中预定义的脚本。可以直接指定完整脚本路径，或使用 skill_path + script_name 的组合。
parameters:
  - name: script_path
    description:
      en_US: Full path to the script (takes priority over skill_path + script_name)
      zh_CN: 脚本的完整路径（优先使用此参数）
    type: string
    required: false
  - name: skill_path
    description:
      en_US: Path to the skill directory (used when script_path is not provided)
      zh_CN: skill 目录路径（当 script_path 未提供时使用）
    type: string
    required: false
  - name: script_name
    description:
      en_US: Name of the script to execute (used when script_path is not provided)
      zh_CN: 要执行的脚本名称（当 script_path 未提供时使用）
    type: string
    required: false
  - name: args
    description:
      en_US: Arguments to pass to the script
      zh_CN: 传递给脚本的参数
    type: object
    required: false
    default: {}
return_description:
  en_US: Returns the execution result from the script (streamed)
  zh_CN: 返回脚本的执行结果（流式输出）
---
