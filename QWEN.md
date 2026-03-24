# Filmeto Project Guidelines

## Project Structure

The Filmeto project follows a well-defined structure to maintain organization and clarity across the codebase.

### Directory Organization

```
filmeto/
├── agent/           # AI agent module with chat, crew, llm, plan, prompt, react, skill, soul, tool
├── app/             # Main application code (config, data, plugins, spi, ui)
├── bin/             # Executable scripts and binaries
├── docs/            # **ALL documentation files must be placed here**
├── examples/        # Example code and demonstrations
├── i18n/            # Internationalization files (en_US, zh_CN)
├── server/          # Backend server implementations (api, plugins, service)
├── style/           # QSS styling files (dark_style.qss, light_style.qss)
├── tests/           # **ALL test files must be placed here**
├── textures/        # Texture and asset files
├── utils/           # Utility functions and helpers
└── workspace/       # Working directory for projects and demos
```

### Detailed Subdirectories

#### agent/ - AI Agent Module
- `chat/` - Chat functionality and conversation handling
- `crew/` - Crew management and orchestration
- `llm/` - Large Language Model integrations
- `plan/` - Planning and execution logic
- `prompt/` - Prompt templates and management
- `react/` - ReAct (Reasoning + Acting) framework
- `skill/` - Skill definitions and implementations
- `soul/` - Agent personality and soul traits
- `tool/` - Tool definitions and integrations

#### app/ - Main Application
- `config/` - Application configuration
- `data/` - Data models and storage
- `plugins/` - Application plugins
- `spi/` - Service Provider Interface
- `ui/` - User interface components

#### server/ - Backend Server
- `api/` - API endpoints
- `plugins/` - Server plugins
- `service/` - Business logic services

#### tests/ - Test Suite
- `react/` - React framework tests
- Test files should mirror the source structure

#### utils/ - Utilities
- `async_queue_utils.py` - Async queue utilities
- `comfy_ui_utils.py` - ComfyUI integration
- `download_utils.py` - Download handling
- `ffmpeg_utils.py` - FFmpeg operations
- `i18n_utils.py` - Internationalization helpers
- `plan_service.py` - Planning service
- `queue_utils.py` - Queue management
- `signal_utils.py` - Qt signal utilities
- `thread_utils.py` - Threading helpers

## Testing Guidelines

### Test File Placement
**CRITICAL: All test files must be placed in the `tests/` directory.** This ensures:

- Consistent location for all test assets
- Easier CI/CD pipeline configuration
- Better project maintainability
- Clear separation between production and test code

### Test Organization
Tests should be organized in subdirectories mirroring the structure of the code being tested:
```
tests/
├── test_app/        # Application tests
├── test_agent/      # Agent module tests
├── test_server/     # Server tests
└── react/           # React framework tests (existing)
```

## Documentation Guidelines

### Documentation File Placement
**CRITICAL: All documentation files must be placed in the `docs/` directory.** This ensures:

- Centralized location for all project documentation
- Consistent access patterns for developers and users
- Proper versioning alongside code changes
- Separation of concerns between code and documentation

### Documentation Types
The docs directory should contain:
- Architecture documentation
- API references
- User guides
- Developer guides
- Release notes
- Contribution guidelines

## Best Practices

1. **Always place new test files in the `tests/` directory**
2. **Always place new documentation files in the `docs/` directory**
3. **Component styles must be defined in global style files (dark_style.qss and light_style.qss) to ensure components can switch between different themes**
4. **Code text should use English and be extracted to global internationalization files (i18n/), providing both en_US and zh_CN language sets**
5. Maintain consistent naming conventions across all directories
6. Keep documentation up-to-date with code changes
7. Write meaningful test cases that cover edge cases and error conditions
8. Use existing utilities from `utils/` before creating new ones
9. Follow the existing module structure when adding new features

Following these guidelines ensures a maintainable, scalable, and well-documented codebase.

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
