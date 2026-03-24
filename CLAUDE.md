# Filmeto - Claude AI Assistant Guidelines

## Project Overview

Filmeto is a Qt-based application with an AI agent architecture. When working on this project, maintain the established structure and follow the guidelines below.

## Project Structure

```
filmeto/
├── agent/           # AI agent module (chat, crew, llm, plan, prompt, react, skill, soul, tool)
├── app/             # Main application (config, data, plugins, spi, ui)
├── bin/             # Executable scripts
├── docs/            # **ALL documentation files**
├── examples/        # Example code and demos
├── i18n/            # Internationalization (en_US, zh_CN)
├── server/          # Backend server (api, plugins, service)
├── style/           # QSS styles (dark_style.qss, light_style.qss)
├── tests/           # **ALL test files**
├── textures/        # Assets and textures
├── utils/           # Utility functions
└── workspace/       # Working directory
```

## Critical Rules

### Test File Placement
**ALL test files MUST be placed in the `tests/` directory.**

When creating tests:
- Organize in subdirectories mirroring the source (e.g., `tests/test_app/`, `tests/test_agent/`)
- Never place test files alongside production code
- Follow naming convention: `test_<module_name>.py`

### Documentation File Placement
**ALL documentation files MUST be placed in the `docs/` directory.**

When creating documentation:
- API references go in `docs/`
- Architecture guides go in `docs/`
- User guides go in `docs/`
- Never create README.md outside of `docs/` (except project root)

### Styling Rules
**Component styles MUST be defined in global QSS files.**

- Use `style/dark_style.qss` for dark theme
- Use `style/light_style.qss` for light theme
- This ensures proper theme switching

### Internationalization
**Code text should use English and be extracted to i18n files.**

- Use `i18n/` directory for translation files
- Provide both `en_US` and `zh_CN` language sets
- Externalize user-facing strings

## Code Standards

1. **Read before modifying** - Always read existing files first
2. **Minimal changes** - Only change what's necessary
3. **No premature abstraction** - Avoid helpers for one-time operations
4. **Consistent naming** - Follow existing conventions
5. **Use existing utilities** - Check `utils/` before creating new helpers

## Before Making Changes

1. Read the relevant files to understand patterns
2. Check if similar functionality already exists
3. Plan your approach before coding
4. Ensure tests go in `tests/`
5. Ensure docs go in `docs/`

## Common Tasks

### Adding a New Agent Feature
1. Read `agent/` to understand the architecture
2. Add to appropriate subdirectory (chat, crew, skill, tool, etc.)
3. Place tests in `tests/test_agent/`
4. Update docs in `docs/`

### Adding UI Components
1. Define styles in `style/dark_style.qss` and `style/light_style.qss`
2. Externalize strings to `i18n/` files
3. Place tests in `tests/test_app/test_ui/`

### Adding Server Features
1. Add to appropriate `server/` subdirectory (api, service, plugins)
2. Place tests in `tests/test_server/`
3. Update API docs in `docs/`

### Working with Utilities
1. Check `utils/` for existing utilities first:
   - `async_queue_utils.py` - async queue operations
   - `download_utils.py` - file downloads
   - `ffmpeg_utils.py` - video processing
   - `i18n_utils.py` - i18n helpers
   - `plan_service.py` - planning logic
   - `queue_utils.py` - queue management
   - `signal_utils.py` - Qt signals
   - `thread_utils.py` - threading
2. Only create new utilities if nothing suitable exists

## Things to Avoid

- Creating test files outside of `tests/`
- Creating documentation files outside of `docs/`
- Adding inline styles that break theme switching
- Hard-coded text that should be internationalized
- Duplicating existing utilities from `utils/`
- Over-engineering simple tasks
- Making changes without reading existing code first

## QML Bridge Principles

When implementing QML-to-Python integration, follow these rules:

1. Principle 1: Keep bridge layering explicit. Do not treat bridge as a universal object.
2. Principle 2: QML must depend only on bridge/ViewModel, not directly on service/domain.
3. Principle 3: Bridge should expose UI semantics, not low-level semantics.
4. Principle 4: QML reads state via `Property`, sends actions via `Slot`, receives events via `Signal`.
5. Principle 5: Avoid letting QML directly modify Python internal state.
6. Principle 6: Every `Property` must provide clear notify signals; state changes must be observable.
7. Principle 7: Complex lists/tables must use Qt Model (`QAbstractListModel` / `QAbstractTableModel`), not ad-hoc object injection.
8. Principle 8: Do not place business logic in QML; keep QML logic presentation-oriented.
9. Principle 9: Keep bridge interfaces small and stable; do not expose the full Python object graph.
10. Principle 11: Bridge must be testable and should not be tightly coupled to QML runtime.
11. Principle 12: Asynchronous work must follow a unified strategy; bridge must not start threads arbitrarily.
12. Principle 13: Follow naming/modularization conventions; prefer names like `XXXViewModel`.
13. Principle 14: Minimize global singleton bridge objects; use singleton only with clear justification.
14. Principle 15: Cross-page behaviors (navigation, dialogs, notifications) must be abstracted centrally, not scattered in QML.
