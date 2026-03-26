"""
Capability Discovery Service

Discovers available capabilities from configured servers and models.
Provides interfaces for capability-based service selection.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from server.api.types import (
    Capability, CapabilityInstance, CapabilityGroup,
    ModelInfo, ModelPricing
)
from server.server import ServerManager, Server

logger = logging.getLogger(__name__)


class CapabilityService:
    """
    Capability discovery service.

    Responsibilities:
    1. Scan all configured servers and discover supported capability instances
    2. Build server:model -> capability instance mapping
    3. Provide query interfaces by capability type
    4. Generate descriptions for LLM selection
    """

    # Capability type to readable name mapping
    CAPABILITY_NAMES = {
        Capability.TEXT2IMAGE: "Text to Image",
        Capability.IMAGE2IMAGE: "Image to Image",
        Capability.IMAGE2VIDEO: "Image to Video",
        Capability.TEXT2VIDEO: "Text to Video",
        Capability.SPEAK2VIDEO: "Speech to Video",
        Capability.TEXT2SPEAK: "Text to Speech",
        Capability.TEXT2MUSIC: "Text to Music",
        Capability.CHAT_COMPLETION: "Chat Completion",
    }

    # Capability type descriptions
    CAPABILITY_DESCRIPTIONS = {
        Capability.TEXT2IMAGE: "Generate images from text descriptions",
        Capability.IMAGE2IMAGE: "Transform or edit images based on prompts",
        Capability.IMAGE2VIDEO: "Animate static images into videos",
        Capability.TEXT2VIDEO: "Generate videos from text descriptions",
        Capability.SPEAK2VIDEO: "Generate avatar videos from speech/audio",
        Capability.TEXT2SPEAK: "Synthesize speech from text",
        Capability.TEXT2MUSIC: "Generate music from text descriptions",
        Capability.CHAT_COMPLETION: "LLM chat completion with streaming support",
    }

    def __init__(self, server_manager: ServerManager):
        """
        Initialize capability service.

        Args:
            server_manager: ServerManager instance for accessing configured servers
        """
        self.server_manager = server_manager
        self._capability_cache: Dict[str, CapabilityInstance] = {}  # key -> instance
        self._capability_by_type: Dict[Capability, List[str]] = {}  # type -> [keys]
        self._model_cache: Dict[str, Dict[str, List[ModelInfo]]] = {}  # server_name -> {capability -> [ModelInfo]}
        self._last_refresh: Optional[datetime] = None

    def refresh_capabilities(self) -> None:
        """
        Refresh capability cache by re-scanning all configured servers.
        """
        self._capability_cache.clear()
        self._capability_by_type.clear()
        self._model_cache.clear()

        for server in self.server_manager.list_servers():
            if not server.is_enabled:
                continue

            try:
                instances, models = self._discover_server_capabilities(server)
                for instance in instances:
                    self._capability_cache[instance.key] = instance

                    # Index by type
                    if instance.capability_type not in self._capability_by_type:
                        self._capability_by_type[instance.capability_type] = []
                    self._capability_by_type[instance.capability_type].append(instance.key)

                # Cache models by server and capability
                if models:
                    self._model_cache[server.name] = models

            except Exception as e:
                logger.error(f"Failed to discover capabilities for server {server.name}: {e}")

        self._last_refresh = datetime.now()
        logger.info(f"Refreshed capabilities: {len(self._capability_cache)} instances found")

    def _discover_server_capabilities(self, server: Server) -> tuple:
        """
        Discover all capability instances supported by a single server.

        Extracts model information from ServerConfig and plugin.yml.

        Args:
            server: Server instance to discover capabilities from

        Returns:
            Tuple of (List of CapabilityInstance objects, Dict of capability -> [ModelInfo])
        """
        instances = []
        models_by_capability: Dict[str, List[ModelInfo]] = {}
        config = server.config
        plugin_info = server.get_plugin_info()

        if not plugin_info:
            return instances, models_by_capability

        # Get capability types from plugin.yml tools section
        for capability in plugin_info.capabilities:
            try:
                capability_type = Capability(capability.name)
            except ValueError:
                logger.warning(f"Unknown capability type: {capability.name}")
                continue

            # Get models from plugin capability config
            model_infos = self._build_model_infos(
                config, capability_type, capability
            )
            models_by_capability[capability_type.value] = model_infos

            # Create capability instances for each model
            for model_info in model_infos:
                key = f"{config.name}:{model_info.name}"

                instance = CapabilityInstance.from_model_info(config.name, model_info)
                instance.metadata.update({
                    "server_type": config.server_type,
                    "plugin_name": config.plugin_name,
                    "engine": plugin_info.engine,
                })
                instances.append(instance)

        return instances, models_by_capability

    def _build_model_infos(
        self,
        config,
        capability_type: Capability,
        capability_config
    ) -> List[ModelInfo]:
        """
        Build ModelInfo objects from plugin capability configuration.

        Args:
            config: ServerConfig instance
            capability_type: Capability type
            capability_config: CapabilityConfig from plugin info

        Returns:
            List of ModelInfo objects
        """
        model_infos = []

        # Get models from plugin capability config
        plugin_models = getattr(capability_config, 'models', []) or []

        if plugin_models:
            # Models defined in plugin
            for model_data in plugin_models:
                model_info = self._create_model_info(
                    model_data, capability_type, config
                )
                model_infos.append(model_info)
        else:
            # Try to extract from server config or create default
            models = self._extract_models_for_capability(
                config, capability_type, capability_config.description
            )

            for model_name, model_info_dict in models.items():
                model_info = ModelInfo(
                    name=model_name,
                    display_name=model_info_dict.get("display_name", model_name),
                    description=model_info_dict.get("description", capability_config.description),
                    capability=capability_type,
                    provider=config.server_type,
                    tags=model_info_dict.get("tags", []),
                    specs=model_info_dict.get("specs", {}),
                    pricing=self._build_pricing(model_info_dict.get("pricing")),
                    is_default=model_info_dict.get("is_default", False),
                    is_available=model_info_dict.get("is_available", True),
                )
                model_infos.append(model_info)

        return model_infos

    def _create_model_info(
        self,
        model_data: Dict[str, Any],
        capability_type: Capability,
        config
    ) -> ModelInfo:
        """
        Create ModelInfo from model configuration dict.

        Args:
            model_data: Model configuration dictionary
            capability_type: Capability type
            config: ServerConfig instance

        Returns:
            ModelInfo object
        """
        return ModelInfo(
            name=model_data.get("name", "default"),
            display_name=model_data.get("display_name", model_data.get("name", "default")),
            description=model_data.get("description", ""),
            capability=capability_type,
            provider=config.server_type,
            version=model_data.get("version", ""),
            detailed_description=model_data.get("detailed_description", ""),
            tags=model_data.get("tags", []),
            specs=model_data.get("specs", {}),
            pricing=self._build_pricing(model_data.get("pricing")),
            is_default=model_data.get("is_default", False),
            is_available=model_data.get("is_available", True),
            metadata=model_data.get("metadata", {}),
        )

    def _build_pricing(self, pricing_data: Optional[Dict[str, Any]]) -> Optional[ModelPricing]:
        """
        Build ModelPricing from pricing configuration.

        Args:
            pricing_data: Pricing configuration dictionary

        Returns:
            ModelPricing object or None
        """
        if not pricing_data:
            return None

        return ModelPricing(
            per_call=pricing_data.get("per_call"),
            per_input_token=pricing_data.get("per_input_token"),
            per_output_token=pricing_data.get("per_output_token"),
            per_second=pricing_data.get("per_second"),
            per_image=pricing_data.get("per_image"),
            custom_unit=pricing_data.get("custom_unit"),
            custom_rate=pricing_data.get("custom_rate"),
        )

    def _extract_models_for_capability(
        self,
        config,
        capability_type: Capability,
        capability_description: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract models for a specific capability from server configuration.

        Strategy:
        1. Check config.parameters.models for capability-specific models
        2. Check for default_model in parameters
        3. Create a default entry if nothing found

        Args:
            config: ServerConfig instance
            capability_type: Capability to extract models for
            capability_description: Default description from plugin.yml

        Returns:
            Dict mapping model_name -> model_info
        """
        models = {}

        # Look for capability-specific models in parameters.models
        raw_models = config.parameters.get("models")
        capability_models_config: Any
        if isinstance(raw_models, dict):
            capability_models_config = raw_models.get(capability_type.value, {})
        elif isinstance(raw_models, list):
            # Bailian and similar plugins persist a flat list of model ids under parameters.models
            capability_models_config = raw_models
        else:
            capability_models_config = {}

        if isinstance(capability_models_config, list):
            # Format: ["model1", "model2"] or [{"name": "model1", ...}]
            for item in capability_models_config:
                if isinstance(item, str):
                    models[item] = {"description": f"Model {item}"}
                elif isinstance(item, dict) and "name" in item:
                    model_name = item.pop("name")
                    models[model_name] = item
        elif isinstance(capability_models_config, dict):
            # Format: {"model1": {...}, "model2": {...}}
            models.update(capability_models_config)

        # If no models found, try default_model or create a default entry
        if not models:
            default_model = config.parameters.get("default_model")
            if default_model:
                models[default_model] = {
                    "description": f"Default model for {capability_type.value}",
                    "is_default": True,
                }
            else:
                # Create a generic default model entry
                models["default"] = {
                    "description": capability_description,
                    "is_default": True,
                }

        return models

    # ------------------------------------------------------------------
    # Public Query Interfaces
    # ------------------------------------------------------------------

    def get_all_capabilities(self) -> List[CapabilityInstance]:
        """
        Get all capability instances.

        Returns:
            List of all CapabilityInstance objects
        """
        if not self._capability_cache:
            self.refresh_capabilities()
        return list(self._capability_cache.values())

    def get_capabilities_by_type(self, tool_type: Capability) -> List[CapabilityInstance]:
        """
        Get capability instances by type.

        Args:
            tool_type: Capability to filter by

        Returns:
            List of CapabilityInstance objects for the given type
        """
        if not self._capability_cache:
            self.refresh_capabilities()

        keys = self._capability_by_type.get(tool_type, [])
        return [self._capability_cache[k] for k in keys if k in self._capability_cache]

    def get_capability(self, key: str) -> Optional[CapabilityInstance]:
        """
        Get a specific capability instance by key.

        Args:
            key: Capability key in "server:model" format

        Returns:
            CapabilityInstance if found, None otherwise
        """
        if not self._capability_cache:
            self.refresh_capabilities()
        return self._capability_cache.get(key)

    def get_capability_groups(self) -> List[CapabilityGroup]:
        """
        Get all capabilities grouped by capability type.

        Returns:
            List of CapabilityGroup objects with instances and models
        """
        if not self._capability_cache:
            self.refresh_capabilities()

        groups = []
        for tool_type in Capability:
            instances = self.get_capabilities_by_type(tool_type)
            if instances:
                # Aggregate unique models from all servers for this capability
                models = self._aggregate_models_for_capability(tool_type)

                group = CapabilityGroup(
                    capability_type=tool_type,
                    capability_name=self.CAPABILITY_NAMES.get(tool_type, tool_type.value),
                    description=self.CAPABILITY_DESCRIPTIONS.get(tool_type, ""),
                    instances=instances,
                    models=models
                )
                groups.append(group)

        return groups

    def _aggregate_models_for_capability(self, capability_type: Capability) -> List[ModelInfo]:
        """
        Aggregate unique models for a capability from all servers.

        Args:
            capability_type: Capability type to get models for

        Returns:
            List of unique ModelInfo objects
        """
        models = []
        seen_names = set()

        for server_name, cap_models in self._model_cache.items():
            cap_name = capability_type.value
            if cap_name in cap_models:
                for model_info in cap_models[cap_name]:
                    # Avoid duplicates by name
                    if model_info.name not in seen_names:
                        seen_names.add(model_info.name)
                        models.append(model_info)

        return models

    def get_models_for_capability(self, capability_type: Capability) -> List[ModelInfo]:
        """
        Get all models available for a specific capability type.

        Args:
            capability_type: Capability type to get models for

        Returns:
            List of ModelInfo objects
        """
        if not self._capability_cache:
            self.refresh_capabilities()

        return self._aggregate_models_for_capability(capability_type)

    def get_capability_keys_by_type(self, tool_type: Capability) -> List[str]:
        """
        Get all capability keys for a specific type.

        Args:
            tool_type: Capability to filter by

        Returns:
            List of keys in "server:model" format
        """
        instances = self.get_capabilities_by_type(tool_type)
        return [inst.key for inst in instances]

    def get_llm_selection_context(
        self,
        tool_type: Capability,
        user_requirement: str = ""
    ) -> Dict[str, Any]:
        """
        Generate context for LLM to select appropriate capability.

        Args:
            tool_type: Capability needed
            user_requirement: User's requirement description

        Returns:
            Dict with capability info formatted for LLM selection
        """
        instances = self.get_capabilities_by_type(tool_type)

        if not instances:
            return {
                "capability_type": tool_type.value,
                "available": False,
                "message": f"No available capabilities for {tool_type.value}"
            }

        # Format instances for LLM with pricing info
        options = []
        for inst in instances:
            option = {
                "key": inst.key,
                "server": inst.server_name,
                "model": inst.model_name,
                "description": inst.description,
                "tags": inst.tags,
                "specs": inst.specs,
                "priority": inst.priority,
            }
            # Include pricing if available
            if inst.pricing:
                option["pricing"] = inst.pricing.to_dict()
            options.append(option)

        return {
            "capability_type": tool_type.value,
            "capability_name": self.CAPABILITY_NAMES.get(tool_type, tool_type.value),
            "available": True,
            "user_requirement": user_requirement,
            "options": options,
            "selection_hint": "Select the most appropriate key based on user requirements, considering tags, specs, priority, and pricing."
        }