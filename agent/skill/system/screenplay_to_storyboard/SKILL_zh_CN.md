---
name: screenplay_to_storyboard
description: 按场景粒度将剧本转换为分镜镜头。每次读取单个剧本场景与该场景已有分镜，分析新增/修改镜头，再按镜头逐个调整并生成关键帧。
tools:
  - screen_play
  - story_board
---

# Screenplay To Storyboard

该技能按“逐场景、逐镜头”方式把剧本转换为分镜：
每个场景先读取剧本与现有分镜，再做差异分析，最后逐个镜头执行创建或更新。

## 导演式分镜方法

将剧本转分镜时，必须采用导演常用流程，而不是机械改写文本：

1. **先抓戏剧意图**：
   - 明确该场景目标、冲突、情绪转折、结尾状态。
   - 先保证观众“该看到什么、该感受到什么”。

2. **拆解视觉节拍**：
   - 将场景拆为 setup -> development -> turn -> payoff 等视觉节拍。
   - 每个节拍映射到一个或多个有明确功能的镜头。

3. **按覆盖策略设计镜头**：
   - 先建立空间（establishing），再主体覆盖（MS/OTS），最后重点特写（CU/insert）。
   - 特写只用于情绪或信息强调，避免滥用。
   - 机位运动要有动机，和场景张力匹配。

4. **保证连续性与方向性**：
   - 默认遵守 180 度规则，除非明确要打破。
   - 保持视线方向和人物方位连续。
   - 新旧镜头不能在空间调度上互相矛盾。

5. **考虑制作可执行性**：
   - 控制镜头数量与复杂度，避免无效冗余。
   - 冗余镜头合并，信息过载镜头拆分。
   - 描述既要简洁，也要能指导拍摄与生成。

## 执行流程

1. 使用 `screen_play` 读取剧本大纲，拿到按顺序处理的 `scene_id` 列表：

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

3. 按场景逐个处理。对每个 `scene_id`：
   - 读取单个剧本场景：

```json
{
  "type": "tool",
  "tool_name": "screen_play",
  "tool_args": {
    "operation": "get",
    "scene_id": "scene_001"
  }
}
```

   - 读取该场景已有分镜：

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "list",
    "scene_id": "scene_001"
  }
}
```

4. 在当前场景内做差异分析并制定镜头计划：
   - 判断哪些镜头需要**新增**（覆盖不足）。
   - 判断哪些镜头需要**修改**（描述或提示词不匹配当前剧本）。
   - 判断哪些镜头需要**删除**（内容为空、冗余或明显不贴合剧本）。
   - 已对齐的镜头保持不变，不要重复创建。

5. 按镜头逐个执行调整（不要批量一把梭）：
   - **新增路径**：

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

   - **修改路径**：

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "update",
    "scene_id": "scene_001",
    "shot_id": "scene_001_shot_001",
    "description": "更新后的分镜描述...",
    "keyframe_context": {
      "prompt": "updated cinematic storyboard frame prompt..."
    }
  }
}
```

   - **删除路径**：

```json
{
  "type": "tool",
  "tool_name": "story_board",
  "tool_args": {
    "operation": "delete",
    "scene_id": "scene_001",
    "shot_id": "scene_001_shot_003"
  }
}
```

6. 每个新增/修改后的镜头都要单独生成（或重生成）关键帧：

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

7. 处理完一个场景再进入下一个场景，直到全部场景完成。最终产物必须是与剧本逐场景对齐的 storyboard shot 集合。

## 单场景分析模板

每个场景至少提取以下结构化信息：

- `scene_goal`：该场景对剧情推进的核心作用。
- `emotional_curve`：情绪起点 -> 转折 -> 终点。
- `blocking_core`：人物相对位置与关键调度。
- `visual_priority`：必须被观众看到的动作/反应/道具信息。
- `shot_strategy`：镜头覆盖策略（建立 / 双人 / OTS / 特写 / 插入 / 转场）。

镜头增改必须由这些字段驱动，不能只复述剧本文字。

## 镜头设计规则

每个镜头都要定义明确 `shot_purpose`（建空间、交代动作、强调反应、揭示信息、过渡）。

- 一个镜头尽量一个主目的。
- 描述应包含：
  - 景别（WS/MS/CU/ECU）
  - 角度（平视/俯拍/仰拍）
  - 运动（静止/摇移/推拉/手持）
  - 主体与动作
  - 光线与氛围关键词
- 避免“电影感很好”这类无叙事功能的空泛表述。

## 新增/修改判定规则

- **新增镜头**：
  - 剧本关键节拍没有被现有分镜覆盖。
  - 现有镜头数不足以清晰交代动作关系。
  - 出现新情绪转折或信息揭示，需要独立镜头强调。

- **修改镜头**：
  - 镜头 id 可保留，但描述与当前剧本不匹配。
  - 人物调度、焦点主体、情绪重点发生变化。
  - 提示词不够具体，影响关键帧质量。

- **保持不变**：
  - 已有镜头在功能与连续性上都正确。

## 删除判定规则（重点）

- **可删除镜头**：
  - 镜头描述为空/无效，已无实质分镜价值。
  - 镜头内容与当前剧本目标、调度明显冲突。
  - 镜头功能重复且影响节奏与连贯性（无明确变体目的）。
  - 镜头破坏连续性（方向、视线、空间逻辑），且非有意设计。

- **删除前检查**：
  - 确认相邻镜头仍能覆盖关键叙事信息。
  - 若删除后会出现叙事空洞，先补新镜头再删除旧镜头。
  - 仅删除“明确不适合”的镜头，避免过度破坏式修改。

## 单场景完成检查清单

进入下一场景前必须满足：

1. 剧本关键节拍都有镜头覆盖。
2. 镜头顺序符合叙事阅读节奏。
3. 所有新增/修改镜头已按需生成（或重生成）关键帧。
4. 对空镜头、冗余镜头、不贴合剧本镜头进行必要删除。
5. 镜头描述可直接用于制作与生成。

## 提示词模板

按镜头使用以下模板填充场景信息：

`Storyboard shot for scene {scene_number}: {title}. {logline}. Location: {location}. Time: {time_of_day}. Characters: {characters}. Visual style: cinematic, clear composition, storyboarding frame, production-ready framing.`

如果关键字段缺失，直接省略，不要编造剧情事实。

## 约束

- 必须遵循：单场景剧本读取 -> 单场景分镜读取 -> 差异分析 -> 逐镜头创建/更新。
- 逐镜头操作可包含 create、update、delete，依据场景贴合度与连贯性判定。
- 每个场景必须先读后改，不允许跳过读取直接写入。
- 对已有优质镜头优先复用，只新增或修改必要镜头。
- 必须使用 `story_board` 工具完成 shot 创建与关键帧生成，不使用 `timeline_item`。
- 除非用户明确要求 `image2image`，默认使用 `text2image`。
- 如果场景信息不明确，优先保守覆盖或最小追问，不编造关键剧情事实。
