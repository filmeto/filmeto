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
    Ability,
    AbilityInstance,
    SelectionConfig,
    SelectionMode,
    SelectionResult,
)
from server.plugins.ability_model_config import (
    get_model_priority,
    get_model_tags,
    is_model_enabled_for_ability,
)
from server.service.ability_service import AbilityService

if TYPE_CHECKING:
    from server.server import ServerManager

logger = logging.getLogger(__name__)


class SelectionError(Exception):
    """Error during ability selection."""
    pass


class AbilitySelectionService:
    """
    Unified server/model selection service.

    Provides a single interface for selecting the best server:model combination
    based on SelectionConfig, supporting all ability types.
    """

    def __init__(self, server_manager: ServerManager):
        self._server_manager = server_manager
        self._ability_service = AbilityService(server_manager)

    def select(self, ability: Ability, config: SelectionConfig) -> SelectionResult:
        if config.mode == SelectionMode.EXACT:
            return self._select_exact(ability, config)
        if config.mode == SelectionMode.SERVER_ONLY:
            return self._select_server_only(ability, config)
        return self._select_auto(ability, config)

    def _select_auto(
        self,
        ability: Ability,
        config: SelectionConfig,
    ) -> SelectionResult:
        instances = self._ability_service.get_ability_instances_by_type(ability)

        if not instances:
            raise SelectionError(
                f"No available instances for ability '{ability.value}'"
            )

        if config.tags:
            instances = [
                inst for inst in instances
                if any(tag in inst.tags for tag in config.tags)
            ]

        if config.min_priority is not None:
            instances = [
                inst for inst in instances
                if inst.priority >= config.min_priority
            ]

        if not instances:
            raise SelectionError(
                f"No instances match filters for ability '{ability.value}' "
                f"(tags={config.tags}, min_priority={config.min_priority})"
            )

        if config.model:
            model_matches = [
                inst for inst in instances
                if inst.model_name == config.model
            ]
            if not model_matches:
                raise SelectionError(
                    f"No instance found with model '{config.model}' for ability "
                    f"'{ability.value}' (tags={config.tags}, min_priority={config.min_priority})"
                )
            instances = model_matches

        instances.sort(key=lambda x: (-x.priority, x.key))
        selected = instances[0]
        candidates_count = len(instances)

        return SelectionResult(
            server_name=selected.server_name,
            model_name=selected.model_name,
            ability_type=ability,
            key=selected.key,
            mode_used=SelectionMode.AUTO,
            instance=selected,
            candidates_count=candidates_count,
            selection_reason=self._build_selection_reason(
                selected, config, candidates_count
            ),
        )

    def _select_server_only(
        self,
        ability: Ability,
        config: SelectionConfig,
    ) -> SelectionResult:
        if not config.server:
            raise SelectionError("SERVER_ONLY mode requires 'server' to be specified")

        instances = self._ability_service.get_ability_instances_by_type(ability)
        instances = [inst for inst in instances if inst.server_name == config.server]

        if not instances:
            raise SelectionError(
                f"No instances found for ability '{ability.value}' "
                f"on server '{config.server}'"
            )

        if config.tags:
            instances = [
                inst for inst in instances
                if any(tag in inst.tags for tag in config.tags)
            ]

        if not instances:
            raise SelectionError(
                f"No instances on server '{config.server}' match tags {config.tags}"
            )

        if config.model:
            model_matches = [
                inst for inst in instances
                if inst.model_name == config.model
            ]
            if not model_matches:
                raise SelectionError(
                    f"Model '{config.model}' not found on server '{config.server}' "
                    f"for ability '{ability.value}'"
                )
            instances = model_matches

        instances.sort(key=lambda x: (-x.priority, x.key))
        selected = instances[0]
        candidates_count = len(instances)

        return SelectionResult(
            server_name=selected.server_name,
            model_name=selected.model_name,
            ability_type=ability,
            key=selected.key,
            mode_used=SelectionMode.SERVER_ONLY,
            instance=selected,
            candidates_count=candidates_count,
            selection_reason=self._build_selection_reason(
                selected, config, candidates_count
            ),
        )

    def _select_exact(self, ability: Ability, config: SelectionConfig) -> SelectionResult:
        if not config.server or not config.model:
            raise SelectionError(
                "EXACT mode requires both 'server' and 'model' to be specified"
            )

        key = f"{config.server}:{config.model}"
        instance = self._ability_service.get_ability_instance(key)

        if not instance:
            raise SelectionError(
                f"Ability instance '{key}' not found for ability '{ability.value}'"
            )

        if not instance.is_available:
            raise SelectionError(
                f"Ability instance '{key}' is not available"
            )

        if instance.ability_type != ability:
            raise SelectionError(
                f"Ability instance '{key}' has type '{instance.ability_type.value}', "
                f"expected '{ability.value}'"
            )

        return SelectionResult(
            server_name=config.server,
            model_name=config.model,
            ability_type=ability,
            key=key,
            mode_used=SelectionMode.EXACT,
            instance=instance,
            candidates_count=1,
            selection_reason=f"Exact selection: {key}",
        )

    def get_default_instance(
        self,
        ability: Ability,
        tags: Optional[List[str]] = None,
    ) -> Optional[AbilityInstance]:
        config = SelectionConfig.auto(tags=tags)
        try:
            result = self.select(ability, config)
            return result.instance
        except SelectionError:
            return None

    def get_all_instances(
        self,
        ability: Ability,
        tags: Optional[List[str]] = None,
        min_priority: Optional[int] = None,
    ) -> List[AbilityInstance]:
        instances = self._ability_service.get_ability_instances_by_type(ability)

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
        selected: AbilityInstance,
        config: SelectionConfig,
        candidates_count: int,
    ) -> str:
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

    def refresh_abilities(self) -> None:
        """Refresh ability cache from server manager."""
        self._ability_service.refresh_abilities()
