# AgentChatListWidget 滚动黑屏问题修复

## 问题描述

在 AgentChatListWidget 中出现两种黑屏情况：
1. **滚动到顶部加载旧消息后**，出现黑屏不显示任何内容
2. **拖拽滚动条时**，出现黑屏不显示任何内容

---

## 问题 1：Prepend 后黑屏

### 根本原因

当用户滚动到顶部触发加载旧消息时：
1. `_load_older_messages` 调用 `_model.prepend_items(items)` 插入新项
2. `_on_rows_inserted` 触发 `_refresh_visible_widgets()`
3. `_refresh_visible_widgets()` 调用 `_rebuild_positions_cache()`
4. `_rebuild_positions_cache()` 调用 `set_row_positions()` **会自动恢复旧滚动位置**
5. 但此时内容已经偏移（前面插入了新内容），导致滚动位置与实际内容不匹配
6. `_restore_scroll_after_prepend()` 尝试调整，但 widget 已被清除且位置计算错误

### 修复方案

#### 1. 添加 `restore_scroll` 参数控制

在 `AgentChatListView.set_row_positions()` 中：

```python
def set_row_positions(self, positions, total_height, restore_scroll=True):
    # ... 更新位置缓存
    if restore_scroll and current_value <= scroll_maximum:
        scrollbar.setValue(current_value)  # 只在允许时恢复滚动位置
```

#### 2. 添加 `_is_prepending` 标志

```python
self._is_prepending = False  # 跟踪 prepend 操作状态
```

#### 3. 在 prepend 期间禁用滚动恢复

```python
def _rebuild_positions_cache(self, force: bool = False):
    # ...
    restore_scroll = not self._is_prepending
    self.list_view.set_row_positions(
        self._row_positions_cache,
        self._total_height_cache,
        restore_scroll=restore_scroll
    )
```

#### 4. 在 `_load_older_messages` 中管理标志

```python
self._is_prepending = True
self._model.prepend_items(items)
QTimer.singleShot(0, lambda: self._restore_scroll_after_prepend(...))
```

```python
def _restore_scroll_after_prepend(self, scrollbar, old_max: int, old_value: int):
    try:
        new_max = scrollbar.maximum()
        delta = new_max - old_max
        scrollbar.setValue(old_value + delta)
    finally:
        self._is_prepending = False  # 清除标志
```

---

## 问题 2：拖拽滚动条时黑屏

### 根本原因

1. **刷新延迟**：16ms 延迟定时器，快速拖拽时刷新被延迟
2. **节流阈值过高**：只有滚动超过 100 像素才触发立即刷新
3. **缓冲区太小**：buffer 只有 2，快速拖拽时 widget 被过早删除
4. **Widget 创建限制**：`MAX_VISIBLE_WIDGETS = 30` 限制了创建数量
5. **缺少视口更新**：创建 widget 后没有强制更新视口

### 修复方案

#### 1. 添加立即刷新选项

```python
def _schedule_visible_refresh(self, immediate: bool = False):
    if immediate:
        self._visible_refresh_timer.stop()
        self._refresh_visible_widgets()  # 立即刷新
    else:
        self._visible_refresh_timer.start(8)  # 从 16ms 减少到 8ms
```

#### 2. 在滚动时使用立即刷新

```python
def _on_scroll_value_changed(self, value: int):
    scroll_diff = abs(value - self._scroll_delta_since_last_refresh)
    if scroll_diff > 50:  # 从 100 降低到 50
        self._scroll_delta_since_last_refresh = value
        self._schedule_visible_refresh(immediate=True)  # 立即刷新
    else:
        self._schedule_visible_refresh(immediate=False)
```

#### 3. 增加滚动时的缓冲区

```python
is_scrolling = (abs(scrollbar.value() - self._scroll_delta_since_last_refresh) > 20)

if is_at_bottom:
    buffer_size = min(20, row_count)
elif is_scrolling:
    buffer_size = 10  # 从 2 增加到 10
    max_to_create = MAX_VISIBLE_WIDGETS * 2  # 创建上限翻倍
else:
    buffer_size = 3  # 从 2 增加到 3
    max_to_create = MAX_VISIBLE_WIDGETS
```

#### 4. 强化范围验证

```python
# 在 _get_visible_row_range 末尾添加验证
if first_row < 0:
    first_row = 0
if first_row >= row_count:
    first_row = row_count - 1
if last_row < first_row:
    last_row = first_row
if last_row >= row_count:
    last_row = row_count - 1

# 最终安全检查
if first_row is None or last_row is None or first_row < 0 or last_row < 0:
    return 0, max(0, row_count - 1)
```

#### 5. 强制视口更新

```python
# 创建 widgets 后强制更新视口
if widgets_to_create or len(self._visible_widgets) < 10:
    self.list_view.viewport().update()
```

---

## 测试方法

### 自动化测试

```bash
python tests/test_app/test_ui/test_agent_chat_list_scroll.py
```

### 手动测试步骤

1. **测试 prepend 黑屏**：
   - 发送足够多的消息（50+ 条）
   - 滚动到顶部加载历史消息
   - 验证消息正确显示，无黑屏

2. **测试拖拽黑屏**：
   - 确保有足够多的消息（100+ 条）
   - 快速拖拽滚动条上下移动
   - 验证始终能看到消息，无黑屏或空白区域

3. **压力测试**：
   - 快速连续拖拽滚动条
   - 在拖拽过程中松开再继续拖拽
   - 验证 UI 响应流畅

---

## 相关文件

- `app/ui/chat/list/agent_chat_list_widget.py` - 主要修复
- `app/ui/chat/list/agent_chat_list_view.py` - 添加 restore_scroll 参数
- `tests/test_app/test_ui/test_agent_chat_list_scroll.py` - 测试界面
- `docs/agent_chat_list_scroll_fix.md` - 本文档

---

## 调试日志

如果问题仍然存在，检查以下日志输出：

```
_refresh_visible_widgets: Invalid range (first_row=None, last_row=None, ...)
_get_visible_row_range: Cache empty, rebuilding (row_count=...)
_get_visible_row_range: Cache still empty after rebuild, returning default range
_get_visible_row_range: Invalid range after calculation, using safe defaults
Error rebuilding positions cache: ...
```

这些日志可以帮助定位问题的具体原因。
