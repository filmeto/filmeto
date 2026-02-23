---
name: execute_generated_code
description:
  en_US: Execute dynamically generated Python code
  zh_CN: 执行动态生成的 Python 代码
parameters:
  - name: code
    description:
      en_US: Python code to execute
      zh_CN: 要执行的 Python 代码
    type: string
    required: true
  - name: args
    description:
      en_US: Arguments to pass to the code
      zh_CN: 传递给代码的参数
    type: object
    required: false
    default: {}
return_description:
  en_US: Returns the execution result from the generated code (streamed)
  zh_CN: 返回代码的执行结果（流式输出）
---
