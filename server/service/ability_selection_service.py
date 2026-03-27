"""
Ability Selection Service

Unified service for selecting server:model combinations based on SelectionConfig.

Supports three selection modes:
- AUTO: Automatically select the best server and model based on priority
- SERVER_ONLY: Select from a specific server, choose best model
- EXACT: Use exact server:model combination
"""

from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from server.api.types import (
    Capability,
    CapabilityInstance,
    SelectionConfig,
    SelectionMode,
    SelectionResult,
)
from server.plugins.ability_model_config import (
    get_model_priority,
    get_model_tags,
    is_model_enabled_for_ability,
)
from server.service.capability_service import CapabilityService

if TYPE_CHECKING:
    from server.server import ServerManager

logger = logging.getLogger(__name__)


class SelectionError(Exception):
    """Error during capability selection."""
    pass


class AbilitySelectionService:
    """
    Unified server/model selection service.

    Provides a single interface for selecting the best server:model combination
    based on SelectionConfig, supporting all 8 capability types.
    """

    def __init__(self, server_manager: ServerManager):
        """
        Initialize selection service.

        Args:
            server_manager: ServerManager instance for accessing servers
        """
        self._server_manager = server_manager
        self._capability_service = CapabilityService(server_manager)

    def select(
        self,
        capability: Capability,
        config: SelectionConfig,
    ) -> SelectionResult:
        """
        Select server:model based on configuration.

        Args:
            capability: The capability type to select for
            config: Selection configuration

        Returns:
            SelectionResult with selected server_name, model_name, and metadata

        Raises:
            SelectionError: If no suitable capability instance is found
        """
        if config.mode == SelectionMode.EXACT:
            return self._select_exact(capability, config)
        elif config.mode == SelectionMode.SERVER_ONLY:
            return self._select_server_only(capability, config)
        else:  # AUTO
            return self._select_auto(capability, config)

    def _select_auto(
        self,
        capability: Capability,
        config: SelectionConfig,
    ) -> SelectionResult:
        """
        AUTO mode: Select best server and model automatically.

        Selection algorithm:
        1. Get all available instances for the capability
        2. Filter by tags if specified
        3. Filter by min_priority if specified
        4. If config.model specified, prefer matching models
        5. Sort by priority (descending) and select highest
        """
        instances = self._capability_service.get_capabilities_by_type(capability)

        if not instances:
            raise SelectionError(
                f"No available instances for capability '{capability.value}'"
            )

        # Apply tag filter
        if config.tags:
            instances = [
                inst for inst in instances
                if any(tag in inst.tags for tag in config.tags)
            ]

        # Apply min_priority filter
        if config.min_priority is not None:
            instances = [
                inst for inst in instances
                if inst.priority >= config.min_priority
            ]

        if not instances:
            raise SelectionError(
                f"No instances match filters for capability '{capability.value}' "
                f"(tags={config.tags}, min_priority={config.min_priority})"
            )

        # If specific model requested, it MUST match (fail if not found)
        if config.model:
            model_matches = [
                inst for inst in instances
                if inst.model_name == config.model
            ]
            if not model_matches:
                raise SelectionError(
                    f"No instance found with model '{config.model}' for capability "
                    f"'{capability.value}' (tags={config.tags}, min_priority={config.min_priority})"
                )
            instances = model_matches

        # Sort by priority (descending), then by name for stability
        instances.sort(key=lambda x: (-x.priority, x.key))

        selected = instances[0]
        candidates_count = len(instances)

        return SelectionResult(
            server_name=selected.server_name,
            model_name=selected.model_name,
            capability_type=capability,
            key=selected.key,
            mode_used=SelectionMode.AUTO,
            instance=selected,
            candidates_count=candidates_count,
            selection_reason=self._build_selection_reason(selected, config, candidates_count),
        )

    def _select_server_only(
        self,
        capability: Capability,
        config: SelectionConfig,
    ) -> SelectionResult:
        """
        SERVER_ONLY mode: Select from specific server, choose best model.

        Algorithm:
        1. Get all instances for the capability
        2. Filter by server_name
        3. If config.model specified, prefer matching models
        4. Sort by priority and select highest
        """
        if not config.server:
            raise SelectionError("SERVER_ONLY mode requires 'server' to be specified")

        instances = self._capability_service.get_capabilities_by_type(capability)

        # Filter by server
        instances = [
            inst for inst in instances
            if inst.server_name == config.server
        ]

        if not instances:
            raise SelectionError(
                f"No instances found for capability '{capability.value}' "
                f"on server '{config.server}'"
            )

        # Apply tag filter if specified
        if config.tags:
            instances = [
                inst for inst in instances
                if any(tag in inst.tags for tag in config.tags)
            ]

        if not instances:
            raise SelectionError(
                f"No instances on server '{config.server}' match tags {config.tags}"
            )

        # If specific model requested, it MUST match (fail if not found)
        if config.model:
            model_matches = [
                inst for inst in instances
                if inst.model_name == config.model
            ]
            if not model_matches:
                raise SelectionError(
                    f"Model '{config.model}' not found on server '{config.server}' "
                    f"for capability '{capability.value}'"
                )
            instances = model_matches

        # Sort by priority (descending)
        instances.sort(key=lambda x: (-x.priority, x.key))

        selected = instances[0]
        candidates_count = len(instances)

        return SelectionResult(
            server_name=selected.server_name,
            model_name=selected.model_name,
            capability_type=capability,
            key=selected.key,
            mode_used=SelectionMode.SERVER_ONLY,
            instance=selected,
            candidates_count=candidates_count,
            selection_reason=self._build_selection_reason(selected, config, candidates_count),
        )

    def _select_exact(
        self,
        capability: Capability,
        config: SelectionConfig,
    ) -> SelectionResult:
        """
        EXACT mode: Use exact server:model combination.

        Validates that the specified combination exists and is available.
        """
        if not config.server or not config.model:
            raise SelectionError(
                "EXACT mode requires both 'server' and 'model' to be specified"
            )

        key = f"{config.server}:{config.model}"
        instance = self._capability_service.get_capability(key)

        if not instance:
            raise SelectionError(
                f"Capability instance '{key}' not found for capability '{capability.value}'"
            )

        if not instance.is_available:
            raise SelectionError(
                f"Capability instance '{key}' is not available"
            )

        if instance.capability_type != capability:
            raise SelectionError(
                f"Capability instance '{key}' has type '{instance.capability_type.value}', "
                f"expected '{capability.value}'"
            )

        return SelectionResult(
            server_name=config.server,
            model_name=config.model,
            capability_type=capability,
            key=key,
            mode_used=SelectionMode.EXACT,
            instance=instance,
            candidates_count=1,
            selection_reason=f"Exact selection: {key}",
        )

    def get_default_instance(
        self,
        capability: Capability,
        tags: Optional[List[str]] = None,
    ) -> Optional[CapabilityInstance]:
        """
        Get the default (highest priority) instance for a capability.

        This is a convenience method for getting the best available instance
        without constructing a full SelectionConfig.

        Args:
            capability: Capability type to get default for
            tags: Optional tag filter

        Returns:
            Best CapabilityInstance or None if no instances available
        """
        config = SelectionConfig.auto(tags=tags)
        try:
            result = self.select(capability, config)
            return result.instance
        except SelectionError:
            return None

    def get_all_instances(
        self,
        capability: Capability,
        tags: Optional[List[str]] = None,
        min_priority: Optional[int] = None,
    ) -> List[CapabilityInstance]:
        """
        Get all available instances for a capability.

        Args:
            capability: Capability type
            tags: Optional tag filter
            min_priority: Optional minimum priority filter

        Returns:
            List of matching CapabilityInstance objects
        """
        instances = self._capability_service.get_capabilities_by_type(capability)

        if tags:
            instances = [
                inst for inst in instances
                if any(tag in inst.tags for tag in tags)
            ]

        if min_priority is not None:
            instances = [
                inst for inst in instances
                if inst.priority >= min_priority
            ]

        return sorted(instances, key=lambda x: (-x.priority, x.key))

    def _build_selection_reason(
        self,
        selected: CapabilityInstance,
        config: SelectionConfig,
        candidates_count: int,
    ) -> str:
        """Build human-readable selection reason."""
        parts = [f"Selected '{selected.key}'"]

        if config.mode == SelectionMode.AUTO:
            parts.append("(auto mode)")
        elif config.mode == SelectionMode.SERVER_ONLY:
            parts.append(f"(server_only mode, server={config.server})")
        else:
            parts.append("(exact mode)")

        if candidates_count > 1:
            parts.append(f"from {candidates_count} candidates")

        if selected.priority > 0:
            parts.append(f"priority={selected.priority}")

        if selected.tags:
            parts.append(f"tags={selected.tags}")

        return " ".join(parts)

    def refresh_capabilities(self) -> None:
        """Refresh capability cache from server manager."""
        self._capability_service.refresh_capabilities()
