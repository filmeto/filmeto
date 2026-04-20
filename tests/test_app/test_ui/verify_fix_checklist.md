# Startup 窗口历史消息显示问题 - 排查步骤

## 问题现象
- test_content_debug.py 能正常显示
- startup 窗口加载的历史消息无法显示

## 已验证
✓ 数据格式一致（Python 和 QML 都使用相同的格式）
✓ 文本提取逻辑正确（safeGet 函数能正确提取 data.text）
✓ QML 组件能正常显示（在测试环境中）

## 排查步骤

### 1. 确认代码版本
检查 AgentMessageBubble.qml 的文本提取逻辑（line 254-267）：

```qml
text: {
    var result = root.safeGet(data, "text", "")
    if (!result) {
        result = root.safeGet(data, "content", "")
    }
    if (!result) {
        var nestedData = root.safeGetData(data, {})
        result = root.safeGet(nestedData, "text", "")
    }
    return result
}
```

如果缺少这个逻辑，说明代码是旧版本。

### 2. 清除 QML 缓存
```bash
# 清除 Qt/QML 缓存
rm -rf ~/.cache/QtProject
rm -rf /tmp/qmlcache*
```

### 3. 重新启动应用
清除缓存后重新启动应用，确保加载最新的 QML 组件。

### 4. 检查调试输出
启动应用后，检查控制台输出：
```
qml: [TextWidget] Computing text - data.keys: [...] result: <text content>
```

如果 `result` 显示文本内容，说明修复生效。

## 预期结果
- 历史消息应该正常显示
- 文本内容应该在 AgentMessageBubble 中可见
- 调试输出应该显示正确的文本内容

## 如果仍然不显示
1. 检查 startup 窗口使用的组件路径是否正确
2. 检查是否有多个 AgentMessageBubble.qml 文件
3. 检查 QML 导入路径是否正确
