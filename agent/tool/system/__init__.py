"""
System tools module.

Tools are now auto-discovered by ToolService from subdirectories.
Each tool has its own directory with:
- tool.md: Metadata definition (YAML frontmatter)
- {tool_name}.py: Tool implementation
- __init__.py: Module exports

No need to manually import and export tools here.
"""

# Tools are auto-discovered by ToolService
# Empty __all__ indicates dynamic loading
__all__ = []
