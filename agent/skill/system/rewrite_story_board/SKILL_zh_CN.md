---
name: rewrite_story_board
description: |-
  Purpose: 根据用户指令重写已有分镜镜头描述。
  Capabilities: 先读取镜头，再仅更新描述和/或关键帧上下文。
  Trigger: 当用户提出“重写镜头”、“调整镜头语气”、“把镜头描述写得更细”时触发。
tools:
  - story_board
---

# 重写分镜 Skill

用于在不改变镜头身份的前提下，重写已有镜头内容。

## 分镜正文重写要求（必须遵循）

- 重写后的正文应符合常见分镜文字表达，不只描述画面内容。
- 必须补齐或明确以下信息（若原文缺失）：
  - 景别与机位角度
  - 运镜路径与节奏（例如缓推、横移、跟拍、手持抖动控制）
  - 拍摄方法（主观/客观、跟焦/甩焦、长镜头/切镜意图）
  - 主体动作、叙事功能与情绪导向
- 保留原镜头叙事目的，不随意改剧情事实；重点提升“可拍性”和“可执行性”。
- 若更新 `keyframe_context.prompt`，须与 `write_story_board` / `screenplay_to_storyboard` 相同：先写强制**漫画线稿分镜**英文前缀，再写镜头画面内容，避免默认照片级写实。

## 推荐流程

1. 读取当前镜头：
```json
{
  "operation": "get",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001"
}
```

2. 写回重写结果：
```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "MS，侧后方 OTS，人物对话时镜头先静止后缓慢横移到反应者面部，并在关键词处短暂停留；采用客观机位与轻微跟焦，突出权力关系变化。"
}
```
