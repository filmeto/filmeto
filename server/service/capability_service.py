"""
Capability Discovery Service

Discovers available capabilities from configured servers and models.
Provides interfaces for capability-based service selection.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from server.api.types import Capability, CapabilityInstance, CapabilityGroup
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
        self._last_refresh: Optional[datetime] = None

    def refresh_capabilities(self) -> None:
        """
        Refresh capability cache by re-scanning all configured servers.
        """
        self._capability_cache.clear()
        self._capability_by_type.clear()

        for server in self.server_manager.list_servers():
            if not server.is_enabled:
                continue

            try:
                instances = self._discover_server_capabilities(server)
                for instance in instances:
                    self._capability_cache[instance.key] = instance

                    # Index by type
                    if instance.capability_type not in self._capability_by_type:
                        self._capability_by_type[instance.capability_type] = []
                    self._capability_by_type[instance.capability_type].append(instance.key)

            except Exception as e:
                logger.error(f"Failed to discover capabilities for server {server.name}: {e}")

        self._last_refresh = datetime.now()
        logger.info(f"Refreshed capabilities: {len(self._capability_cache)} instances found")

    def _discover_server_capabilities(self, server: Server) -> List[CapabilityInstance]:
        """
        Discover all capability instances supported by a single server.

        Extracts model information from ServerConfig and plugin.yml.

        Args:
            server: Server instance to discover capabilities from

        Returns:
            List of CapabilityInstance objects
        """
        instances = []
        config = server.config
        plugin_info = server.get_plugin_info()

        if not plugin_info:
            return instances

        # Get capability types from plugin.yml tools section
        for tool in plugin_info.tools:
            try:
                tool_type = Capability(tool.name)
            except ValueError:
                logger.warning(f"Unknown tool type: {tool.name}")
                continue

            # Get models supported by this tool
            models = self._extract_models_for_tool(config, tool_type, tool.description)

            for model_name, model_info in models.items():
                key = f"{config.name}:{model_name}"

                instance = CapabilityInstance(
                    key=key,
                    server_name=config.name,
                    model_name=model_name,
                    capability_type=tool_type,
                    description=model_info.get("description", tool.description),
                    detailed_description=model_info.get("detailed_description", ""),
                    tags=model_info.get("tags", []),
                    specs=model_info.get("specs", {}),
                    priority=model_info.get("priority", 0),
                    is_available=model_info.get("is_available", True),
                    metadata={
                        "server_type": config.server_type,
                        "plugin_name": config.plugin_name,
                        "engine": plugin_info.engine,
                    }
                )
                instances.append(instance)

        return instances

    def _extract_models_for_tool(
        self,
        config,
        tool_type: Capability,
        tool_description: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract models for a specific tool from server configuration.

        Strategy:
        1. Check config.parameters.models for tool-specific models
        2. Check for default_model in parameters
        3. Create a default entry if nothing found

        Args:
            config: ServerConfig instance
            tool_type: Capability to extract models for
            tool_description: Default description from plugin.yml

        Returns:
            Dict mapping model_name -> model_info
        """
        models = {}

        # Look for tool-specific models in parameters.models
        tool_models_config = config.parameters.get("models", {}).get(tool_type.value, {})

        if isinstance(tool_models_config, list):
            # Format: ["model1", "model2"] or [{"name": "model1", ...}]
            for item in tool_models_config:
                if isinstance(item, str):
                    models[item] = {"description": f"Model {item}"}
                elif isinstance(item, dict) and "name" in item:
                    model_name = item.pop("name")
                    models[model_name] = item
        elif isinstance(tool_models_config, dict):
            # Format: {"model1": {...}, "model2": {...}}
            models.update(tool_models_config)

        # If no models found, try default_model or create a default entry
        if not models:
            default_model = config.parameters.get("default_model")
            if default_model:
                models[default_model] = {
                    "description": f"Default model for {tool_type.value}",
                    "is_default": True,
                }
            else:
                # Create a generic default model entry
                models["default"] = {
                    "description": tool_description,
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
            List of CapabilityGroup objects
        """
        if not self._capability_cache:
            self.refresh_capabilities()

        groups = []
        for tool_type in Capability:
            instances = self.get_capabilities_by_type(tool_type)
            if instances:
                group = CapabilityGroup(
                    capability_type=tool_type,
                    capability_name=self.CAPABILITY_NAMES.get(tool_type, tool_type.value),
                    description=self.CAPABILITY_DESCRIPTIONS.get(tool_type, ""),
                    instances=instances
                )
                groups.append(group)

        return groups

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

        # Format instances for LLM
        options = []
        for inst in instances:
            options.append({
                "key": inst.key,
                "server": inst.server_name,
                "model": inst.model_name,
                "description": inst.description,
                "tags": inst.tags,
                "specs": inst.specs,
                "priority": inst.priority,
            })

        return {
            "capability_type": tool_type.value,
            "capability_name": self.CAPABILITY_NAMES.get(tool_type, tool_type.value),
            "available": True,
            "user_requirement": user_requirement,
            "options": options,
            "selection_hint": "Select the most appropriate key based on user requirements, considering tags, specs, and priority."
        }