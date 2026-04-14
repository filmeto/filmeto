---
name: screenplay_to_storyboard
description: 将剧本场景转换为分镜镜头（shot），并为每个镜头生成关键帧。适用于用户要求把 screenplay/script 转为 storyboard、shot card、分镜草图的场景。
tools:
  - screen_play
  - story_board
---

# Screenplay To Storyboard

该技能用于把剧本场景转换为分镜镜头：每个分镜先创建为 storyboard shot，再触发一次关键帧生成。

## 执行流程

1. 使用 `screen_play` 读取剧本大纲：

```json
{
  "type": "tool",
  "tool_name": "screen_play",
  "tool_args": {
    "operation": "outline",
    "include_content": true,
    "sort_by": "scene_number"
  }
}
```

2. 如果没有场景，停止并提示用户先创建剧本场景。

3. 基于场景构建分镜提示词：
- 优先使用 `logline`、`location`、`time_of_day`、`characters`、`story_beat`、`content`。
- 默认每个场景生成一个分镜；若用户要求可生成多分镜。
- 提示词保持视觉化、简洁。

4. 对每个分镜先调用 `story_board` 创建 shot：

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "create",
    "scene_id": "scene_001",
    "description": "Storyboard shot for scene ...",
    "keyframe_context": {
      "prompt": "cinematic storyboard frame, ..."
    }
  }
}
```

5. 然后调用 `story_board` 为该 shot 生成关键帧：

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "text2image",
    "scene_id": "scene_001",
    "shot_id": "scene_001_shot_001",
    "prompt": "cinematic storyboard frame, ...",
    "width": 1024,
    "height": 1024
  }
}
```

6. 按场景顺序处理全部分镜，确保每个生成结果都绑定到对应的 storyboard shot。

## 提示词模板

使用以下模板填充场景信息：

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

如果关键字段缺失，直接省略，不要编造剧情事实。

## 约束

- 一个计划分镜对应一个 storyboard shot。
- 必须使用 `story_board` 工具完成 shot 创建与关键帧生成，不使用 `timeline_item`。
- 除非用户明确要求 `image2image`，默认使用 `text2image`。
