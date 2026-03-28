"""
LLM Service Module

Implements the LlmService class to wrap LiteLLM functionality and integrate with
the system settings service to manage AI model configurations.

This service can use either:
1. Server's ChatService (recommended) - Uses the unified selection system
2. Direct LiteLLM calls - For backward compatibility
"""
import os
from typing import Optional, Dict, Any, AsyncIterator, List, Union
import litellm
from app.data.settings import Settings
from utils.i18n_utils import translation_manager

# Register custom model prices for models not in LiteLLM's default cost map
# This prevents DEBUG warnings about unmapped models
CUSTOM_MODEL_PRICES = {
    # Qwen3.5 series models (DashScope)
    "qwen3.5-flash": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.0000003,  # $0.3 per 1M tokens
        "output_cost_per_token": 0.0000006,  # $0.6 per 1M tokens
        "litellm_provider": "dashscope",
    },
    "qwen3.5-plus": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.0000008,  # $0.8 per 1M tokens
        "output_cost_per_token": 0.000002,  # $2 per 1M tokens
        "litellm_provider": "dashscope",
    },
    # Kimi K2 series models (Moonshot)
    "kimi-k2.5": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.000001,  # $1 per 1M tokens
        "output_cost_per_token": 0.000002,  # $2 per 1M tokens
        "litellm_provider": "openai",
    },
    "kimi-k2-thinking": {
        "max_tokens": 16384,
        "input_cost_per_token": 0.000002,  # $2 per 1M tokens
        "output_cost_per_token": 0.000004,  # $4 per 1M tokens
        "litellm_provider": "openai",
    },
    # GLM series models (Zhipu AI)
    "glm-5": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.000001,  # $1 per 1M tokens
        "output_cost_per_token": 0.000001,  # $1 per 1M tokens
        "litellm_provider": "openai",
    },
    "glm-4.7": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.0000005,  # $0.5 per 1M tokens
        "output_cost_per_token": 0.0000005,  # $0.5 per 1M tokens
        "litellm_provider": "openai",
    },
}

# Register custom model prices with LiteLLM
for model_name, model_info in CUSTOM_MODEL_PRICES.items():
    litellm.model_cost[model_name] = model_info
    # Also register with dashscope prefix, but update provider to dashscope
    dashscope_model_info = model_info.copy()
    dashscope_model_info["litellm_provider"] = "dashscope"
    litellm.model_cost[f"dashscope/{model_name}"] = dashscope_model_info


class LlmService:
    """
    Service class that wraps LiteLLM functionality and integrates with system settings.

    This class is responsible for:
    - Retrieving OpenAI settings from the system settings service
    - Initializing LiteLLM with the retrieved settings
    - Providing a clean interface to LiteLLM's functionality
    - Supporting special handling for different AI service providers like DashScope
    - Using server's ChatService for unified model selection (always enabled)
    """

    # Class-level cache for ChatService instance
    _chat_service = None
    _server_manager = None

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

    @classmethod
    def get_chat_service(cls):
        """
        Get or create the server's ChatService instance.

        Uses lazy initialization to avoid circular imports.
        Returns None if server is not available.
        """
        if cls._chat_service is None:
            try:
                from server.server import ServerManager
                from server.service.chat_service import ChatService
                from server.plugins.plugin_manager import PluginManager
                from pathlib import Path

                # Get workspace path
                project_root = Path(__file__).parent.parent.parent
                workspace_path = project_root / "workspace"

                # Create plugin manager and server manager
                plugin_manager = PluginManager()
                plugin_manager.discover_plugins()
                cls._server_manager = ServerManager(str(workspace_path), plugin_manager)

                # Create chat service
                cls._chat_service = ChatService(cls._server_manager)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to initialize ChatService: {e}")
                return None

        return cls._chat_service

    @classmethod
    def set_chat_service(cls, chat_service, server_manager=None):
        """
        Set the ChatService instance externally.

        This is useful when the server is already initialized elsewhere.
        """
        cls._chat_service = chat_service
        cls._server_manager = server_manager
    
    def _detect_provider_from_base_url(self, base_url: str) -> str:
        """Detect the provider type from the base URL."""
        if not base_url:
            return "openai"

        if 'dashscope.aliyuncs.com' in base_url:
            return "dashscope"
        elif '.openai.azure.com' in base_url or 'openai.azure.com' in base_url:
            return "azure"
        elif 'anthropic' in base_url:
            return "anthropic"
        elif 'cohere' in base_url:
            return "cohere"
        elif 'replicate' in base_url:
            return "replicate"
        else:
            # Default to openai for custom endpoints that are OpenAI-compatible
            return "openai"

    def _map_model_for_provider(self, model: str, provider: str) -> str:
        """
        Map model names to provider-specific model names if needed.

        Args:
            model: The original model name
            provider: The provider type ('openai', 'dashscope', etc.)

        Returns:
            Provider-specific model name
        """
        if provider == "dashscope":
            # Common mappings for DashScope models
            model_mappings = {
                # Standard OpenAI models to DashScope equivalents
                "gpt-4": "qwen-max",  # Using Qwen as equivalent to GPT-4
                "gpt-4o": "qwen-max",  # Using Qwen as equivalent to GPT-4o
                "gpt-4o-mini": "qwen-turbo",  # Using Qwen-Turbo as equivalent to GPT-4o-mini
                "gpt-4-turbo": "qwen-max",  # Using Qwen-Max as equivalent to GPT-4-Turbo
                "gpt-3.5-turbo": "qwen-turbo",  # Using Qwen-Turbo as equivalent to GPT-3.5
                "gpt-3.5": "qwen-turbo",  # Using Qwen-Turbo as equivalent to GPT-3.5

                # Anthropic models to DashScope equivalents
                "claude-3-opus": "qwen-max",  # Using Qwen-Max as equivalent to Claude-3-Opus
                "claude-3-sonnet": "qwen-max",  # Using Qwen-Max as equivalent to Claude-3-Sonnet
                "claude-3-haiku": "qwen-turbo",  # Using Qwen-Turbo as equivalent to Claude-3-Haiku
                "claude-2.1": "qwen-max",  # Using Qwen-Max as equivalent to Claude-2.1

                # Google models to DashScope equivalents
                "gemini-pro": "qwen-max",  # Using Qwen-Max as equivalent to Gemini-Pro
                "gemini-1.5-pro": "qwen-max",  # Using Qwen-Max as equivalent to Gemini-1.5-Pro
                "gemini-1.5-flash": "qwen-turbo",  # Using Qwen-Turbo as equivalent to Gemini-1.5-Flash

                # Embedding models
                "text-embedding-3-small": "text-embedding-v1",
                "text-embedding-3-large": "text-embedding-v1",
                "text-embedding-ada-002": "text-embedding-v1",

                # Add more mappings as needed
            }

            # Get the mapped model name
            mapped_model = model_mappings.get(model, model)

            # Prepend 'dashscope/' prefix for LiteLLM to recognize the provider
            if not mapped_model.startswith('dashscope/'):
                mapped_model = f'dashscope/{mapped_model}'

            return mapped_model
        else:
            # For other providers, just return the model as-is
            # But still prepend the provider prefix for consistency
            if not model.startswith(provider + '/') and provider != "openai":
                model = f'{provider}/{model}'
            return model

    def _initialize_from_settings(self):
        """Initialize the service by retrieving settings from the system settings service."""
        if self.settings:
            # Retrieve settings from environment variables (AI service settings removed from UI)
            self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
            self.api_base = os.getenv('OPENAI_BASE_URL') or os.getenv('OPENAI_HOST')
            self.default_model = os.getenv('DEFAULT_MODEL', 'qwen3.5-flash')

            # Detect provider from base URL
            self.provider = self._detect_provider_from_base_url(self.api_base)

            # Map the default model to provider-specific model if needed
            self.default_model = self._map_model_for_provider(self.default_model, self.provider)

            # Set LiteLLM configurations
            if self.api_key:
                litellm.api_key = self.api_key
            if self.api_base:
                # Set the API base for the detected provider
                if self.provider == "dashscope":
                    # For DashScope, use the compatible mode endpoint with proper provider prefix
                    litellm.custom_api_base = self.api_base
                    # Set headers for DashScope if needed
                    litellm.default_headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                else:
                    litellm.api_base = self.api_base
        else:
            # Fallback to environment variables if no settings service is provided
            self.api_key = os.getenv('OPENAI_API_KEY') or os.getenv('DASHSCOPE_API_KEY')
            self.api_base = os.getenv('OPENAI_BASE_URL', os.getenv('OPENAI_HOST'))
            self.default_model = os.getenv('DEFAULT_MODEL', 'qwen3.5-flash')

            # Detect provider from base URL
            self.provider = self._detect_provider_from_base_url(self.api_base)

            # Map the default model to provider-specific model if needed
            self.default_model = self._map_model_for_provider(self.default_model, self.provider)

            # Set LiteLLM configurations
            if self.api_key:
                litellm.api_key = self.api_key
            if self.api_base:
                # Set the API base for the detected provider
                if self.provider == "dashscope":
                    # For DashScope, use the compatible mode endpoint with proper provider prefix
                    litellm.custom_api_base = self.api_base
                    # Set headers for DashScope if needed
                    litellm.default_headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                else:
                    litellm.api_base = self.api_base

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
            litellm.api_key = api_key

        if api_base:
            self.api_base = api_base
            # Update provider based on the new API base
            self.provider = self._detect_provider_from_base_url(self.api_base)

            # Set the API base for the detected provider
            if self.provider == "dashscope":
                # For DashScope, use the compatible mode endpoint with proper provider prefix
                litellm.custom_api_base = self.api_base
                # Set headers for DashScope if needed
                litellm.default_headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"} if self.api_key else {"Content-Type": "application/json"}
            else:
                litellm.api_base = self.api_base

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
            **kwargs: Additional arguments to pass to LiteLLM

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

        # Fallback to direct LiteLLM call only if server is not available
        return await self._acompletion_via_litellm(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=stream,
            **kwargs
        )

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
            # Convert to litellm-compatible format
            return self._convert_server_response(response)

    async def _stream_via_server(self, chat_service, request):
        """
        Stream response from server's ChatService.
        Yields litellm-compatible streaming chunks.
        """
        async for chunk in chat_service.chat_completion_stream(request):
            # Convert ChatCompletionChunk to litellm-compatible format
            yield self._convert_server_chunk(chunk)

    def _convert_server_response(self, response) -> Any:
        """
        Convert ChatCompletionResponse to litellm-compatible format.
        """
        from litellm import ModelResponse

        # Create a ModelResponse that mimics litellm's response structure
        choices = []
        for choice in response.choices:
            from litellm.utils import Choices, Message
            msg = Message(
                role=choice.message.role,
                content=choice.message.content,
            )
            if choice.message.tool_calls:
                msg.tool_calls = choice.message.tool_calls
            choices.append(Choices(
                finish_reason=choice.finish_reason,
                index=choice.index,
                message=msg,
            ))

        return ModelResponse(
            id=response.id,
            choices=choices,
            created=response.created,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        )

    def _convert_server_chunk(self, chunk) -> Any:
        """
        Convert ChatCompletionChunk to litellm-compatible streaming chunk.
        """
        from litellm.utils import StreamingChoices

        choices = []
        for choice in chunk.choices:
            from litellm.utils import Delta
            delta = Delta(
                role=choice.delta.role if choice.delta.role else None,
                content=choice.delta.content if choice.delta.content else None,
            )
            choices.append(StreamingChoices(
                finish_reason=choice.finish_reason,
                index=choice.index,
                delta=delta,
            ))

        return type('StreamingChunk', (), {
            'id': chunk.id,
            'choices': choices,
            'created': chunk.created,
            'model': chunk.model,
        })()

    async def _acompletion_via_litellm(self,
                                        model: str,
                                        messages: list,
                                        temperature: float,
                                        stream: bool,
                                        **kwargs) -> Any:
        """
        Execute completion directly via LiteLLM (fallback method).
        """
        # Add any additional configuration from settings
        kwargs.setdefault('temperature', temperature)

        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's acompletion normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return await litellm.acompletion(
            model=model,
            messages=messages,
            stream=stream,
            base_url=self.api_base,
            api_base=self.api_base,
            **kwargs
        )
    
    def completion(self,
                   model: Optional[str] = None,
                   messages: Optional[list] = None,
                   temperature: Optional[float] = None,
                   **kwargs) -> Any:
        """
        Sync completion method that wraps LiteLLM's completion function.

        Args:
            model: Model to use for completion (defaults to self.default_model)
            messages: List of messages for the conversation
            temperature: Temperature setting (defaults to self.temperature)
            **kwargs: Additional arguments to pass to LiteLLM

        Returns:
            Completion response from LiteLLM
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

        # Add any additional configuration from settings
        kwargs.setdefault('temperature', temperature)

        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's completion normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return litellm.completion(
            model=model,
            messages=messages,
            base_url=self.api_base,
            api_base=self.api_base,
            **kwargs
        )
    
    async def aembedding(self,
                        model: str,
                        input_text: str) -> Any:
        """
        Async embedding method that wraps LiteLLM's aembedding function.

        Args:
            model: Model to use for embeddings
            input_text: Text to generate embeddings for

        Returns:
            Embedding response from LiteLLM
        """
        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's aembedding normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return await litellm.aembedding(
            model=model,
            input=input_text,
            base_url=self.api_base,
            api_base=self.api_base
        )

    def embedding(self,
                  model: str,
                  input_text: str) -> Any:
        """
        Sync embedding method that wraps LiteLLM's embedding function.

        Args:
            model: Model to use for embeddings
            input_text: Text to generate embeddings for

        Returns:
            Embedding response from LiteLLM
        """
        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's embedding normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return litellm.embedding(
            model=model,
            input=input_text,
            base_url=self.api_base,
            api_base=self.api_base
        )
    
    async def atranscription(self,
                            model: str,
                            audio_file_path: str) -> Any:
        """
        Async transcription method that wraps LiteLLM's atranscription function.

        Args:
            model: Model to use for transcription
            audio_file_path: Path to the audio file to transcribe

        Returns:
            Transcription response from LiteLLM
        """
        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's atranscription normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return await litellm.atranscription(
            model=model,
            file=audio_file_path,
            base_url=self.api_base,
            api_base=self.api_base
        )

    def transcription(self,
                      model: str,
                      audio_file_path: str) -> Any:
        """
        Sync transcription method that wraps LiteLLM's transcription function.

        Args:
            model: Model to use for transcription
            audio_file_path: Path to the audio file to transcribe

        Returns:
            Transcription response from LiteLLM
        """
        # Map the model to provider-specific model if needed
        model = self._map_model_for_provider(model, self.provider)

        # Call LiteLLM's transcription normally - it will handle provider-specific logic internally
        # Explicitly pass base_url to ensure custom endpoints are used correctly
        # Note: base_url is the standard LiteLLM parameter; api_base is kept for compatibility
        return litellm.transcription(
            model=model,
            file=audio_file_path,
            base_url=self.api_base,
            api_base=self.api_base
        )
    
    def list_models(self) -> list:
        """
        List available models from LiteLLM.
        
        Returns:
            List of available models
        """
        return litellm.model_list
    
    def validate_config(self) -> bool:
        """
        Validate if the LLM service is properly configured.

        Returns:
            True if properly configured, False otherwise
        """
        # Check if either API key is set OR API base is set (for custom endpoints)
        # This allows for services that might use different authentication methods
        return bool(self.api_key) or bool(self.api_base)
    
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

        Handles litellm ModelResponse objects (Pydantic models) and extracts
        the message content. Supports both regular content and reasoning_content
        for reasoning models.

        Args:
            response: The response object from litellm (ModelResponse)

        Returns:
            The extracted content as a string, or empty string if extraction fails.
        """
        # Handle litellm ModelResponse object (Pydantic model)
        # ModelResponse structure: response.choices[0].message.content
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