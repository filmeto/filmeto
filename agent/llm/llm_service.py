"""
LLM Service Module

Implements the LlmService class that provides chat completion functionality
through the server's ChatService with the unified selection system.
"""
import os
from typing import Optional, Dict, Any, AsyncIterator, List, Union

from app.data.settings import Settings
from utils.i18n_utils import translation_manager


class LlmService:
    """
    Service class that provides LLM chat completion functionality via server plugins.

    This class is responsible for:
    - Retrieving configuration from environment or Bailian plugin config
    - Providing chat completion through server's ChatService (unified selection system)
    - Supporting language prompt injection for multi-language support
    """

    def __init__(self, workspace=None):
        """
        Initialize the LlmService.

        Args:
            workspace: Workspace instance containing settings. If not provided, will use environment variables.
        """
        self.workspace = workspace
        self.settings = getattr(workspace, 'settings', None) if workspace else None
        self.api_key = None
        self.api_base = None
        self.default_model = 'qwen3.5-flash'
        self.temperature = 0.7
        # Instance-level cache for ChatService
        self._chat_service = None
        self._server_manager = None
        self.language_prompts = {
            'zh_CN': '请使用中文回答。',
            'en_US': 'Please respond in English.',
            'ja_JP': '日本語で返答してください。',
            'ko_KR': '한국어로 대답해 주세요.',
            'fr_FR': 'Veuillez répondre en français.',
            'de_DE': 'Bitte antworten Sie auf Deutsch.',
            'es_ES': 'Por favor, responda en español.'
        }

        # Initialize the service
        self._initialize_from_settings()

    def get_chat_service(self):
        """
        Get or create the server's ChatService instance.

        Uses lazy initialization to avoid circular imports.
        Returns None if server is not available.
        """
        if self._chat_service is None:
            try:
                from server.server import ServerManager
                from server.service.chat_service import ChatService
                from server.plugins.plugin_manager import PluginManager
                from pathlib import Path

                # Get workspace path - use instance workspace if available
                workspace_path = None
                if self.workspace and hasattr(self.workspace, 'get_path'):
                    workspace_path = self.workspace.get_path()
                elif self.workspace and hasattr(self.workspace, 'workspace_path'):
                    workspace_path = self.workspace.workspace_path

                # Fallback to default workspace if not available
                if not workspace_path:
                    project_root = Path(__file__).parent.parent.parent
                    workspace_path = str(project_root / "workspace")

                # Create plugin manager and server manager
                plugin_manager = PluginManager()
                plugin_manager.discover_plugins()
                self._server_manager = ServerManager(workspace_path, plugin_manager)

                # Create chat service
                self._chat_service = ChatService(self._server_manager)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to initialize ChatService: {e}")
                return None

        return self._chat_service

    def set_chat_service(self, chat_service, server_manager=None):
        """
        Set the ChatService instance externally.

        This is useful when the server is already initialized elsewhere.
        """
        self._chat_service = chat_service
        self._server_manager = server_manager

    def _initialize_from_settings(self):
        """Initialize the service by retrieving settings from environment or Bailian plugin config."""
        # First try environment variables
        self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
        self.api_base = os.getenv('OPENAI_BASE_URL') or os.getenv('OPENAI_HOST')
        self.default_model = os.getenv('DEFAULT_MODEL', 'qwen3.5-flash')

        # If no API key from environment, try to get from Bailian plugin config
        if not self.api_key and self.workspace:
            bailian_config = self._get_bailian_config()
            if bailian_config:
                self.api_key = bailian_config.get('api_key', '')
                self.api_base = bailian_config.get('api_base', '')
                # Use default_model from config if set
                if bailian_config.get('default_model'):
                    self.default_model = bailian_config.get('default_model')

    def _get_bailian_config(self) -> Optional[Dict[str, Any]]:
        """Get Bailian plugin configuration from workspace servers directory."""
        try:
            if not self.workspace:
                return None

            # Get workspace path
            workspace_path = self.workspace.get_path() if hasattr(self.workspace, 'get_path') else None
            if not workspace_path:
                return None

            # Check for Bailian server config in servers directory
            import yaml
            from pathlib import Path

            servers_dir = Path(workspace_path) / "servers"
            bailian_server_dir = servers_dir / "bailian"

            if not bailian_server_dir.exists():
                return None

            config_path = bailian_server_dir / "server.yml"
            if not config_path.exists():
                return None

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                return None

            # ServerConfig has api_key at top level, and plugin-specific config in parameters
            bailian_config = {}

            # Get api_key from top level
            api_key = config.get('api_key', '')
            if api_key:
                bailian_config['api_key'] = api_key

            # Get plugin-specific config from parameters
            parameters = config.get('parameters', {}) or {}

            # Merge parameters into bailian_config
            bailian_config.update(parameters)

            # Build API base from endpoint if not explicitly set
            api_base = bailian_config.get('api_base')
            if not api_base:
                # Default to DashScope chat endpoint
                from server.plugins.bailian_server.models_config import models_config
                api_base = models_config.get_dashscope_chat_endpoint()

            bailian_config['api_base'] = api_base

            return bailian_config

        except Exception as e:
            # Silently fail - configuration might not exist yet
            return None

    def get_current_language(self) -> str:
        """
        Get the current language from the translation manager.

        Returns:
            Current language code (e.g., 'zh_CN', 'en_US')
        """
        return translation_manager.get_current_language()

    def _inject_language_prompt(self, messages: list) -> list:
        """
        Inject language instruction as system prompt if not already present.

        Args:
            messages: List of messages to potentially modify

        Returns:
            Modified list of messages with language prompt injected if needed
        """
        if not messages:
            return messages

        # Get current language
        current_language = self.get_current_language()
        language_instruction = self.language_prompts.get(current_language, '')

        if not language_instruction:
            # No language instruction defined for this language
            return messages

        # Check if there's already a system message
        has_system_message = any(msg.get('role') == 'system' for msg in messages)

        if has_system_message:
            # If there's already a system message, we'll append our language instruction
            # to the first system message we find
            for msg in messages:
                if msg.get('role') == 'system':
                    current_content = msg.get('content', '')
                    if language_instruction not in current_content:
                        msg['content'] = f"{current_content}\n\n{language_instruction}".strip()
                    break
        else:
            # If there's no system message, insert one at the beginning
            messages = [
                {"role": "system", "content": language_instruction}
            ] + messages

        return messages

    def configure(self, api_key: Optional[str] = None, api_base: Optional[str] = None,
                  default_model: Optional[str] = None, temperature: Optional[float] = None):
        """
        Configure the LLM service with specific parameters.

        Args:
            api_key: OpenAI API key
            api_base: OpenAI API base URL
            default_model: Default model to use
            temperature: Temperature setting for the model
        """
        if api_key:
            self.api_key = api_key

        if api_base:
            self.api_base = api_base

        if default_model:
            self.default_model = default_model

        if temperature is not None:
            self.temperature = temperature

    async def acompletion(self,
                         model: Optional[str] = None,
                         messages: Optional[list] = None,
                         temperature: Optional[float] = None,
                         stream: bool = False,
                         server: Optional[str] = None,
                         selection: Optional[Dict[str, Any]] = None,
                         **kwargs) -> Any:
        """
        Async completion method that uses server's ChatService.

        This method always uses the server's ChatService with the unified selection system.

        Args:
            model: Model to use for completion (defaults to self.default_model)
            messages: List of messages for the conversation
            temperature: Temperature setting (defaults to self.temperature)
            stream: Whether to stream the response
            server: Optional server name for SERVER_ONLY selection mode
            selection: Optional selection configuration dict (e.g., {"mode": "auto", "tags": ["fast"]})
            **kwargs: Additional arguments

        Returns:
            Completion response from ChatService
        """
        # Use defaults if not provided
        if model is None:
            model = self.default_model
        if temperature is None:
            temperature = self.temperature
        if messages is None:
            messages = []

        # Inject language prompt based on current language setting
        messages = self._inject_language_prompt(messages)

        # Always use server's ChatService
        chat_service = self.get_chat_service()
        if chat_service is not None:
            return await self._acompletion_via_server(
                chat_service=chat_service,
                model=model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                server=server,
                selection=selection,
                **kwargs
            )

        # If no server available, raise an error
        raise RuntimeError("ChatService not available. Please ensure the server is properly configured.")

    async def _acompletion_via_server(self,
                                       chat_service,
                                       model: Optional[str],
                                       messages: list,
                                       temperature: float,
                                       stream: bool,
                                       server: Optional[str] = None,
                                       selection: Optional[Dict[str, Any]] = None,
                                       **kwargs) -> Any:
        """
        Execute completion via server's ChatService.

        This method uses the unified selection system for model/server selection.
        """
        from server.api.chat_types import ChatCompletionRequest, ChatMessage

        # Refresh capabilities to get latest server status (e.g., enabled/disabled)
        try:
            selection_svc = chat_service.selection_service
            if selection_svc and hasattr(selection_svc, '_capability_service'):
                selection_svc._capability_service.refresh_capabilities()
        except Exception:
            pass  # Ignore refresh errors

        # Convert messages to ChatMessage format
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle multi-modal content
                chat_messages.append(ChatMessage(role=role, content=content))
            else:
                chat_messages.append(ChatMessage(role=role, content=content))

        # Build selection config
        selection_config = None
        if selection:
            selection_config = selection
        elif server:
            # If server is specified, use SERVER_ONLY mode
            selection_config = {"mode": "server_only", "server": server}

        # Create request
        request = ChatCompletionRequest(
            model=model,  # Can be None for AUTO mode
            messages=chat_messages,
            temperature=temperature,
            stream=stream,
            server=server,
            selection=selection_config,
        )

        # Add any additional kwargs that ChatCompletionRequest supports
        if "max_tokens" in kwargs:
            request.max_tokens = kwargs["max_tokens"]
        if "top_p" in kwargs:
            request.top_p = kwargs["top_p"]
        if "stop" in kwargs:
            request.stop = kwargs["stop"]
        if "tools" in kwargs:
            request.tools = kwargs["tools"]
        if "tool_choice" in kwargs:
            request.tool_choice = kwargs["tool_choice"]

        if stream:
            # Return async generator for streaming
            return self._stream_via_server(chat_service, request)
        else:
            # Non-streaming call
            response = await chat_service.chat_completion(request)
            # Convert to compatible format for agent consumption
            return self._convert_server_response(response)

    async def _stream_via_server(self, chat_service, request):
        """
        Stream response from server's ChatService.
        Yields compatible streaming chunks for agent consumption.
        """
        async for chunk in chat_service.chat_completion_stream(request):
            # Convert ChatCompletionChunk to compatible format
            yield self._convert_server_chunk(chunk)

    def _convert_server_response(self, response) -> Any:
        """
        Convert ChatCompletionResponse to a compatible format.

        Creates a simple object with choices that mimics the structure expected by agents.
        """
        class Message:
            def __init__(self, role, content, tool_calls=None):
                self.role = role
                self.content = content
                self.tool_calls = tool_calls

        class Choice:
            def __init__(self, index, message, finish_reason):
                self.index = index
                self.message = message
                self.finish_reason = finish_reason

        choices = []
        for choice in response.choices:
            msg = Message(
                role=choice.message.role,
                content=choice.message.content,
                tool_calls=choice.message.tool_calls,
            )
            choices.append(Choice(
                index=choice.index,
                message=msg,
                finish_reason=choice.finish_reason,
            ))

        class Usage:
            def __init__(self, prompt_tokens, completion_tokens, total_tokens):
                self.prompt_tokens = prompt_tokens
                self.completion_tokens = completion_tokens
                self.total_tokens = total_tokens

        usage = Usage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        class ModelResponse:
            def __init__(self, id, choices, created, model, usage):
                self.id = id
                self.choices = choices
                self.created = created
                self.model = model
                self.usage = usage

        return ModelResponse(
            id=response.id,
            choices=choices,
            created=response.created,
            model=response.model,
            usage=usage,
        )

    def _convert_server_chunk(self, chunk) -> Any:
        """
        Convert ChatCompletionChunk to compatible streaming chunk format.
        """
        class Delta:
            def __init__(self, role=None, content=None):
                self.role = role
                self.content = content

        class StreamingChoice:
            def __init__(self, index, delta, finish_reason):
                self.index = index
                self.delta = delta
                self.finish_reason = finish_reason

        choices = []
        for choice in chunk.choices:
            delta = Delta(
                role=choice.delta.role if choice.delta.role else None,
                content=choice.delta.content if choice.delta.content else None,
            )
            choices.append(StreamingChoice(
                index=choice.index,
                delta=delta,
                finish_reason=choice.finish_reason,
            ))

        class StreamingChunk:
            def __init__(self, id, choices, created, model):
                self.id = id
                self.choices = choices
                self.created = created
                self.model = model

        return StreamingChunk(
            id=chunk.id,
            choices=choices,
            created=chunk.created,
            model=chunk.model,
        )

    def validate_config(self) -> bool:
        """
        Validate if the LLM service is properly configured.

        Returns:
            True if properly configured, False otherwise
        """
        # Check if either API key is set OR API base is set
        if self.api_key or self.api_base:
            return True

        # If no API key/base in LlmService, check if ChatService can be initialized
        # This allows configuration to come from server-side (e.g., Bailian plugin config)
        try:
            chat_service = self.get_chat_service()
            if chat_service is not None:
                # Refresh capabilities to get latest server status
                selection_svc = chat_service.selection_service
                if selection_svc and hasattr(selection_svc, '_capability_service'):
                    selection_svc._capability_service.refresh_capabilities()

                # Check if there are any available chat capabilities
                from server.api.types import Capability
                capabilities = selection_svc._capability_service.get_capabilities_by_type(Capability.CHAT_COMPLETION)
                if capabilities:
                    return True
        except Exception:
            pass

        return False

    def get_current_config(self) -> Dict[str, Any]:
        """
        Get the current configuration of the LLM service.

        Returns:
            Dictionary containing current configuration
        """
        return {
            'api_key_set': bool(self.api_key),
            'api_base': self.api_base,
            'default_model': self.default_model,
            'temperature': self.temperature
        }

    @staticmethod
    def extract_content(response: Any) -> str:
        """
        Extract content from LLM response.

        Handles response objects with choices attribute and extracts
        the message content. Supports both regular content and reasoning_content
        for reasoning models.

        Args:
            response: The response object with choices attribute

        Returns:
            The extracted content as a string, or empty string if extraction fails.
        """
        # Handle response object with choices (our custom format or litellm-compatible)
        if hasattr(response, 'choices'):
            choices = response.choices
            if choices and len(choices) > 0:
                choice = choices[0]
                if hasattr(choice, 'message'):
                    message = choice.message
                    # First try to get regular content
                    if hasattr(message, 'content') and message.content is not None:
                        return str(message.content)
                    # Check for reasoning_content (for reasoning models like o1)
                    if hasattr(message, 'reasoning_content') and message.reasoning_content:
                        return str(message.reasoning_content)
                # Fallback to text attribute (for some older response formats)
                text = getattr(choice, 'text', None)
                if text:
                    return str(text)

        # Fallback: convert to string
        return str(response) if response else ""