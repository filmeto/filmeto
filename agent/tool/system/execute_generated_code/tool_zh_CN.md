---
name: execute_generated_code
description: 执行动态生成的 Python 代码
parameters:
  - name: code
    description: 要执行的 Python 代码
    type: string
    required: true
  - name: args
    description: 传递给代码的参数
    type: object
    required: false
    default: {}
return_description: 返回代码的执行结果（流式输出）
---
