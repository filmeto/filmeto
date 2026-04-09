---
name: screenplay_to_storyboard
description: 将剧本场景转换为分镜时间线卡片，并为每个分镜提交文生图任务。适用于用户要求把 screenplay/script 转为 storyboard、shot card、timeline 分镜草图的场景。
tools:
  - screen_play
  - timeline_item
---

# Screenplay To Storyboard

该技能用于把剧本场景转换为分镜卡片：每个分镜对应一个 timeline item，并触发一次文生图生成。

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

4. 对每个分镜调用 `timeline_item` 创建/编辑并提交文生图：

```json
{
  "type": "tool",
  "tool_name": "timeline_item",
  "tool_args": {
    "operation": "create",
    "prompt": "cinematic storyboard frame, ...",
    "ability": "text2image",
    "submit_task": true
  }
}
```

5. 按场景顺序处理全部分镜，最后一个处理的 timeline item 保持选中状态。

## 提示词模板

使用以下模板填充场景信息：

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

如果关键字段缺失，直接省略，不要编造剧情事实。

## 约束

- 一个分镜对应一个 timeline item。
- 除非用户明确要求其他能力，否则统一使用 `text2image`。
- 必须通过 `timeline_item` 工具保持与界面一致的时间线行为，不直接修改底层文件。
