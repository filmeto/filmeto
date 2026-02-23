import sys
import runpy
import io
import contextlib
import logging
import importlib
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING, AsyncGenerator
from .base_tool import BaseTool, ToolMetadata
from .tool_context import ToolContext

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class ToolService:
    """
    Service to manage and execute tools.
    Provides interfaces for executing scripts and individual tools.
    """

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_system_tools()

    def _register_system_tools(self):
        """Register all system tools by discovering tool directories."""
        try:
            system_dir = Path(__file__).parent / 'system'
            if not system_dir.exists():
                logger.warning(f"System tools directory not found: {system_dir}")
                return

            # Discover and register tools from subdirectories
            for tool_dir in sorted(system_dir.iterdir()):
                if tool_dir.is_dir() and not tool_dir.name.startswith('_'):
                    self._register_tool_from_directory(tool_dir)

            # Fallback to old __all__ based registration if no directories found
            if not self.tools:
                logger.info("No tool directories found, falling back to __all__ based registration")
                self._register_system_tools_legacy()

        except Exception as e:
            # If system tools are not available, continue without registering them
            logger.warning(f"System tools not available: {e}", exc_info=True)

    def _register_system_tools_legacy(self):
        """Legacy method to register system tools from __all__ export."""
        try:
            from .system import __all__ as system_tools

            # Dynamically register all system tools
            for tool_class_name in system_tools:
                # Import the tool class dynamically
                module = importlib.import_module('.system', package=__package__)
                tool_class = getattr(module, tool_class_name)

                # Create an instance and register it
                tool_instance = tool_class()
                self.register_tool(tool_instance)
        except ImportError as e:
            logger.warning(f"System tools not available (legacy): {e}", exc_info=True)

    def _register_tool_from_directory(self, tool_dir: Path):
        """
        Register a tool from its directory.

        The directory should contain:
        - A Python module file (e.g., tool_name.py or __init__.py)
        - A tool.md file with metadata (optional, for metadata-driven tools)

        Args:
            tool_dir: Path to the tool directory
        """
        import os

        tool_name = tool_dir.name

        # Try to find the tool class
        tool_class = self._find_tool_class(tool_dir)
        if tool_class is None:
            logger.warning(f"No tool class found in {tool_dir}")
            return

        # Create an instance
        try:
            tool_instance = tool_class()

            # Set _tool_dir for metadata loading
            tool_instance._tool_dir = tool_dir

            # Register the tool
            self.register_tool(tool_instance)
            logger.debug(f"Registered tool: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to instantiate tool {tool_name}: {e}", exc_info=True)

    def _find_tool_class(self, tool_dir: Path) -> Optional[type]:
        """
        Find the tool class in a tool directory.

        The tool class can be defined in:
        1. A Python module file matching the directory name (e.g., create_plan.py)
        2. The __init__.py file

        The tool class should follow the naming convention: {ToolName}Tool
        (e.g., CreatePlanTool for a tool named "create_plan")

        Args:
            tool_dir: Path to the tool directory

        Returns:
            The tool class, or None if not found
        """
        tool_name = tool_dir.name

        # Convert tool_name to class name (e.g., create_plan -> CreatePlanTool)
        # Handle special cases
        class_name_suffix = "Tool"
        if tool_name == "video_timeline":
            expected_class_name = "VideoTimelineTool"
        else:
            # Convert snake_case to PascalCase and add "Tool" suffix
            expected_class_name = "".join(
                word.capitalize() for word in tool_name.split("_")
            ) + class_name_suffix

        # Try to import from various possible module locations
        possible_modules = []

        # 1. Check for {tool_name}.py file
        for py_file in tool_dir.glob(f"{tool_name}.py"):
            possible_modules.append(f".system.{tool_name}.{tool_name}")

        # 2. Check for {tool_name}_tool.py file (for video_timeline_tool.py)
        for py_file in tool_dir.glob(f"{tool_name}_tool.py"):
            module_name = py_file.stem
            possible_modules.append(f".system.{tool_name}.{module_name}")

        # 3. Check __init__.py
        init_file = tool_dir / "__init__.py"
        if init_file.exists():
            possible_modules.append(f".system.{tool_name}")

        # Try each possible module
        for module_name in possible_modules:
            try:
                module = importlib.import_module(module_name, package=__package__)

                # Look for the expected class name
                if hasattr(module, expected_class_name):
                    return getattr(module, expected_class_name)

                # Look for any class ending with "Tool"
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, BaseTool) and
                            attr is not BaseTool):
                        return attr

            except (ImportError, AttributeError) as e:
                logger.debug(f"Failed to import {module_name}: {e}")
                continue

        return None

    @contextmanager
    def _sys_path_manager(self, project_root: str):
        """Context manager to temporarily add project root to sys.path."""
        original_path = sys.path.copy()
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        try:
            yield
        finally:
            sys.path[:] = original_path

    @contextmanager
    def _sys_argv_manager(self, new_argv: list):
        """Context manager to temporarily modify sys.argv."""
        import sys
        original_argv = sys.argv[:]
        sys.argv = new_argv if new_argv is not None else ['']
        try:
            yield
        finally:
            sys.argv[:] = original_argv

    def _find_project_root(self, start_path: Path) -> Path:
        """
        Find the project root by looking for typical project markers.

        Args:
            start_path: Path to start searching from

        Returns:
            Path to the project root directory
        """
        current_path = start_path.resolve()

        # Common project root indicators
        markers = ['.git', 'setup.py', 'pyproject.toml', 'requirements.txt', 'main.py']

        while current_path.parent != current_path:  # Stop at filesystem root
            if any((current_path / marker).exists() for marker in markers):
                return current_path
            current_path = current_path.parent

        # If no markers found, return the filesystem root
        return start_path.parent

    def register_tool(self, tool: BaseTool):
        """Register a new tool with the service."""
        self.tools[tool.name] = tool

    def _create_tool_event(
        self,
        event_type: str,
        tool_name: str,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
        **kwargs
    ) -> Any:
        """
        Create a ReactEvent for tool execution.

        Args:
            event_type: Type of event (tool_start, tool_progress, tool_end, error)
            tool_name: Name of the tool being executed
            project_name: Project name
            react_type: React type
            run_id: Run ID
            step_id: Step ID
            sender_id: ID of the event sender
            sender_name: Display name of the event sender
            **kwargs: Additional event-specific data

        Returns:
            ReactEvent object
        """
        from agent.event.agent_event import AgentEvent
        from agent.chat.content import (
            ToolCallContent, ProgressContent, ErrorContent
        )

        # Create appropriate content based on event type
        content = None

        if event_type == "tool_start":
            content = ToolCallContent(
                tool_name=tool_name,
                tool_input=kwargs.get("input", {}),
                title=f"Tool: {tool_name}",
                description="Tool execution started"
            )
        elif event_type == "tool_progress":
            content = ProgressContent(
                progress=kwargs.get("progress", ""),
                tool_name=tool_name,
                title="Tool Execution",
                description="Tool execution in progress"
            )
        elif event_type == "tool_end":
            content = ToolCallContent(
                tool_name=tool_name,
                tool_input=kwargs.get("input", {}),
                result=kwargs.get("result"),
                error=kwargs.get("error"),
                tool_status="completed" if not kwargs.get("error") else "failed",
                title=f"Tool Result: {tool_name}",
                description=f"Tool execution {'completed' if not kwargs.get('error') else 'failed'}"
            )
            if not kwargs.get("error"):
                content.complete()
            else:
                content.fail()
        elif event_type == "error":
            content = ErrorContent(
                error_message=kwargs.get("error", "Unknown error"),
                error_type=kwargs.get("error_type"),
                details=kwargs.get("details"),
                title="Error",
                description="Tool execution error"
            )

        return AgentEvent.create(
            event_type=event_type,
            project_name=project_name,
            react_type=react_type,
            run_id=run_id,
            step_id=step_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content
        )

    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[ToolContext] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
        sender_id: str = "",
        sender_name: str = "",
    ) -> AsyncGenerator[Any, None]:
        """
        Execute a specific tool with given parameters.

        Yields ReactEvent objects for tracking execution progress.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Optional ToolContext object containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking
            sender_id: ID of the event sender
            sender_name: Display name of the event sender

        Yields:
            ReactEvent objects with types: tool_start, tool_progress, tool_end, error

        Raises:
            ValueError: If tool is not found
        """
        if tool_name not in self.tools:
            yield self._create_tool_event(
                "error",
                tool_name,
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=f"Tool '{tool_name}' not found"
            )
            return

        tool = self.tools[tool_name]

        # Yield tool_start event
        yield self._create_tool_event(
            "tool_start",
            tool_name,
            project_name,
            react_type,
            run_id,
            step_id,
            sender_id,
            sender_name,
            parameters=parameters
        )

        try:
            # Tool.execute is now an async method that yields ReactEvent objects directly
            async for event in tool.execute(
                parameters=parameters,
                context=context,
                project_name=project_name,
                react_type=react_type,
                run_id=run_id,
                step_id=step_id,
                sender_id=sender_id,
                sender_name=sender_name,
            ):
                # Yield the event directly - tools now create proper ReactEvent objects
                yield event

        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)
            yield self._create_tool_event(
                "error",
                tool_name,
                project_name,
                react_type,
                run_id,
                step_id,
                sender_id,
                sender_name,
                error=str(e)
            )

    def _create_script_tool_wrapper(
        self,
        context: Optional[ToolContext],
        project_name: str,
        react_type: str,
        run_id: str,
        step_id: int,
    ):
        """Create a synchronous wrapper for execute_tool to be used in scripts.

        This function is called from synchronous scripts and needs to
        properly handle the async execute_tool method.

        Args:
            context: ToolContext object containing workspace and project info
            project_name: Project name for event tracking
            react_type: React type for event tracking
            run_id: Run ID for event tracking
            step_id: Step ID for event tracking

        Returns:
            A synchronous function that wraps execute_tool
        """
        import asyncio
        import concurrent.futures

        def script_execute_tool(script_tool_name: str, parameters: Dict[str, Any]):
            """Synchronous execute_tool wrapper for script execution."""

            async def _collect_result():
                """Collect the final result from execute_tool events."""
                result = None
                async for event in self.execute_tool(
                    script_tool_name,
                    parameters,
                    context,
                    project_name,
                    react_type,
                    run_id,
                    step_id,
                ):
                    if event.event_type == "tool_end":
                        # Extract from content or payload (backward compat)
                        if event.content and hasattr(event.content, 'result'):
                            result = event.content.result
                        elif event.payload:
                            result = event.payload.get("result")
                        return result
                    elif event.event_type == "error":
                        # Extract from content or payload (backward compat)
                        if event.content and hasattr(event.content, 'error_message'):
                            error_msg = event.content.error_message
                        elif event.payload:
                            error_msg = event.payload.get("error", "Unknown error")
                        else:
                            error_msg = "Unknown error"
                        raise RuntimeError(error_msg)
                return result

            # Get the current event loop (if any)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context - run in a separate thread with its own loop
                    def run_in_new_loop():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(_collect_result())
                        finally:
                            new_loop.close()

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result(timeout=30)  # 30 second timeout
                else:
                    # No loop running, safe to use asyncio.run
                    return asyncio.run(_collect_result())
            except RuntimeError:
                # No event loop exists, create one
                return asyncio.run(_collect_result())

        return script_execute_tool

    def _ensure_context_has_project_and_llm(
        self,
        context: Optional[ToolContext],
    ) -> Optional[ToolContext]:
        """
        Ensure the ToolContext has project and llm_service populated from workspace.

        This method populates the context with project and llm_service if they are
        not already set, by fetching them from the workspace.

        Args:
            context: ToolContext object to enhance

        Returns:
            The enhanced ToolContext or None if context is invalid
        """
        if not context or not context.workspace:
            return context

        # If project is not set, try to get it from workspace
        if context.project is None:
            try:
                project_manager = context.workspace.get_project_manager() if hasattr(context.workspace, 'get_project_manager') else None
                if project_manager and context.project_name:
                    context.project = project_manager.get_project(context.project_name)
                elif hasattr(context.workspace, 'get_project'):
                    context.project = context.workspace.get_project()
            except Exception as e:
                logger.warning(f"Failed to get project from workspace: {e}")

        # If llm_service is not set, try to get it from workspace
        if context.llm_service is None:
            if hasattr(context.workspace, 'get_llm_service'):
                try:
                    context.llm_service = context.workspace.get_llm_service()
                except Exception as e:
                    logger.warning(f"Failed to get llm_service from workspace: {e}")

        return context

    async def execute_script(
        self,
        script_path: str,
        argv: list = None,
        context: Optional[ToolContext] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
    ) -> Any:
        """
        Execute a script that can call various tools.

        Returns the script execution result (captured stdout).

        Args:
            script_path: Absolute path to the script file to execute
            argv: Optional list of command-line arguments to pass to the script
            context: Optional ToolContext object containing workspace and project info
            project_name: Project name for event tracking (unused, for compatibility)
            react_type: React type for event tracking (unused, for compatibility)
            run_id: Run ID for event tracking (unused, for compatibility)
            step_id: Step ID for event tracking (unused, for compatibility)

        Returns:
            The script execution result (captured stdout), or raises an exception on error
        """
        # Ensure context has project and llm_service populated
        context = self._ensure_context_has_project_and_llm(context)

        # Create the execute_tool wrapper for scripts
        script_execute_tool = self._create_script_tool_wrapper(
            context, project_name, react_type, run_id, step_id
        )

        # ToolContext now provides the same interface as SkillContext
        # Use 'context' as the variable name for skill scripts
        script_globals = {
            '__builtins__': __builtins__,
            'execute_tool': script_execute_tool,
            'tool_context': context,  # For scripts explicitly using ToolContext
            'context': context,  # For skill scripts (was SkillContext, now ToolContext)
        }

        # Determine project root directory - look for typical project markers
        script_dir = Path(script_path).parent
        project_root = self._find_project_root(script_dir)

        # Execute the script using runpy.run_path with the context managers
        try:
            # Capture stdout during script execution
            captured_output = io.StringIO()

            with self._sys_path_manager(str(project_root)), self._sys_argv_manager(argv), \
                 contextlib.redirect_stdout(captured_output):
                # Run the script with the prepared globals
                runpy.run_path(script_path, init_globals=script_globals, run_name="__main__")

            # Get the captured output and return it
            output = captured_output.getvalue()
            return output.rstrip() if output else None

        except SyntaxError as e:
            logger.error(f"Syntax error in script '{script_path}': {e}", exc_info=True)
            raise ValueError(f"Syntax error in script: {str(e)}")
        except FileNotFoundError:
            logger.error(f"Script file not found: {script_path}", exc_info=True)
            raise FileNotFoundError(f"Script file not found: {script_path}")
        except Exception as e:
            logger.error(f"Error executing script '{script_path}': {e}", exc_info=True)
            raise RuntimeError(f"Error executing script: {str(e)}")

    async def execute_script_content(
        self,
        script_content: str,
        argv: list = None,
        context: Optional[ToolContext] = None,
        project_name: str = "",
        react_type: str = "",
        run_id: str = "",
        step_id: int = 0,
    ) -> Any:
        """
        Execute a Python script from content string.

        Supports executing dynamically generated Python code.

        Returns the script execution result (captured stdout).

        Args:
            script_content: Python code as string
            argv: Optional list of command-line arguments to pass to the script
            context: Optional ToolContext object containing workspace and project info
            project_name: Project name for event tracking (unused, for compatibility)
            react_type: React type for event tracking (unused, for compatibility)
            run_id: Run ID for event tracking (unused, for compatibility)
            step_id: Step ID for event tracking (unused, for compatibility)

        Returns:
            The script execution result (captured stdout), or raises an exception on error
        """
        import tempfile
        import os

        # Create the execute_tool wrapper for scripts
        script_execute_tool = self._create_script_tool_wrapper(
            context, project_name, react_type, run_id, step_id
        )

        script_globals = {
            '__builtins__': __builtins__,
            'execute_tool': script_execute_tool,
            'tool_context': context,
        }

        # Create temp file and execute
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_script_path = f.name
            f.write(script_content)

        try:
            captured_output = io.StringIO()
            project_root = self._find_project_root(Path.cwd())

            with self._sys_path_manager(str(project_root)), self._sys_argv_manager(argv), \
                 contextlib.redirect_stdout(captured_output):
                runpy.run_path(temp_script_path, init_globals=script_globals, run_name="__main__")

            output = captured_output.getvalue()
            return output.rstrip() if output else None

        except SyntaxError as e:
            logger.error(f"Syntax error in script content: {e}", exc_info=True)
            raise ValueError(f"Syntax error: {str(e)}")
        except Exception as e:
            logger.error(f"Execution error in script content: {e}", exc_info=True)
            raise RuntimeError(f"Execution error: {str(e)}")
        finally:
            try:
                os.unlink(temp_script_path)
            except OSError:
                pass

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())

    def get_tool_metadata(self, tool_name: str, lang: str = "en_US") -> ToolMetadata:
        """
        Get metadata for a specific tool.

        Args:
            tool_name: Name of the tool
            lang: Language code for localized metadata (e.g., "en_US", "zh_CN")

        Returns:
            ToolMetadata object containing the tool's metadata

        Raises:
            ValueError: If tool is not found
        """
        if tool_name not in self.tools:
            logger.error(f"Tool '{tool_name}' not found in available tools: {list(self.tools.keys())}", exc_info=True)
            raise ValueError(f"Tool '{tool_name}' not found")

        tool = self.tools[tool_name]
        return tool.metadata(lang)

    def get_all_tools_metadata(self, lang: str = "en_US") -> List[ToolMetadata]:
        """
        Get metadata for all available tools.

        Args:
            lang: Language code for localized metadata (e.g., "en_US", "zh_CN")

        Returns:
            List of ToolMetadata objects for all available tools
        """
        return [tool.metadata(lang) for tool in self.tools.values()]

    def get_tools_metadata_by_names(self, tool_names: List[str], lang: str = "en_US") -> List[ToolMetadata]:
        """
        Get metadata for tools by their names.

        Args:
            tool_names: List of tool names to get metadata for
            lang: Language code for localized metadata (e.g., "en_US", "zh_CN")

        Returns:
            List of ToolMetadata objects for the specified tools

        Raises:
            ValueError: If any tool is not found
        """
        metadata_list = []
        for tool_name in tool_names:
            if tool_name not in self.tools:
                logger.error(f"Tool '{tool_name}' not found in available tools: {list(self.tools.keys())}", exc_info=True)
                raise ValueError(f"Tool '{tool_name}' not found")
            tool = self.tools[tool_name]
            metadata_list.append(tool.metadata(lang))
        return metadata_list
