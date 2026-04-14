---
name: write_story_board
description: |-
  Purpose: 创建和更新分镜镜头。
  Capabilities: 新建镜头、更新镜头描述、更新关键帧上下文元数据。
  Trigger: 当用户提出“新增镜头”、“写分镜”、“修改镜头描述”、“编辑分镜镜头”时触发。
tools:
  - story_board
---

# 写分镜 Skill

用于分镜的非删除类编辑（创建/更新）。

## 分镜正文写作规范（必须遵循）

- 分镜正文必须使用常见的分镜文字风格，按“镜头语法 + 画面叙事”描述，不得只写静态画面。
- 每条 `description` 至少覆盖以下维度：
  - 景别（WS/MS/CU/ECU 等）
  - 机位角度（平视/俯拍/仰拍等）
  - 运镜方式（静止/推拉/摇移/跟拍/手持等）及其动机
  - 拍摄方法（主观/客观、跟焦、长镜头、插入镜头等必要信息）
  - 主体动作与叙事意图（该镜头要交代什么）
- 避免仅写“某人站在某处”这类画面复述；要写清楚“怎么拍、为何这么拍、观众会接收到什么信息”。
- 文字应可直接指导拍摄与生成，不使用空泛词（如“很有电影感”）。

## 创建镜头

```json
{
  "operation": "create",
  "scene_id": "scene_001",
  "description": "CU，平视近距离，主角在闪烁街灯下缓慢打开生锈金属盒；镜头由静止轻推近并跟焦到盒内关键物件，以强化信息揭示时刻。",
  "keyframe_context": {
    "prompt": "cinematic close-up, noir lighting, rain droplets",
    "ability_model": "wanx",
    "reference_images": []
  }
}
```

## 更新镜头

```json
{
  "operation": "update",
  "scene_id": "scene_001",
  "shot_id": "scene_001_shot_001",
  "description": "更新后的镜头描述..."
}
```

## 约束

- 不用于删除操作；删除请使用 `delete_story_board`。
- `scene_id` 必填。
