"""
Ability discovery service.

Discovers available abilities from configured servers and models.
Provides interfaces for ability-based service selection.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from server.api.types import (
    Ability,
    AbilityInstance,
    AbilityGroup,
    ModelInfo,
    ModelPricing,
)
from server.server import ServerManager, Server
from server.plugins.ability_model_config import is_model_enabled_for_ability

logger = logging.getLogger(__name__)


class AbilityService:
    """
    Ability discovery service.

    Responsibilities:
    1. Scan all configured servers and discover supported ability instances
    2. Build server:model -> ability instance mapping
    3. Provide query interfaces by ability type
    4. Generate descriptions for LLM selection
    """

    ABILITY_NAMES = {
        Ability.TEXT2IMAGE: "Text to Image",
        Ability.IMAGE2IMAGE: "Image to Image",
        Ability.IMAGE2VIDEO: "Image to Video",
        Ability.TEXT2VIDEO: "Text to Video",
        Ability.SPEAK2VIDEO: "Speech to Video",
        Ability.TEXT2SPEAK: "Text to Speech",
        Ability.TEXT2MUSIC: "Text to Music",
        Ability.CHAT_COMPLETION: "Chat Completion",
    }

    ABILITY_DESCRIPTIONS = {
        Ability.TEXT2IMAGE: "Generate images from text descriptions",
        Ability.IMAGE2IMAGE: "Transform or edit images based on prompts",
        Ability.IMAGE2VIDEO: "Animate static images into videos",
        Ability.TEXT2VIDEO: "Generate videos from text descriptions",
        Ability.SPEAK2VIDEO: "Generate avatar videos from speech/audio",
        Ability.TEXT2SPEAK: "Synthesize speech from text",
        Ability.TEXT2MUSIC: "Generate music from text descriptions",
        Ability.CHAT_COMPLETION: "LLM chat completion with streaming support",
    }

    def __init__(self, server_manager: ServerManager):
        self.server_manager = server_manager
        self._ability_cache: Dict[str, AbilityInstance] = {}
        self._abilities_by_type: Dict[Ability, List[str]] = {}
        self._model_cache: Dict[str, Dict[str, List[ModelInfo]]] = {}
        self._last_refresh: Optional[datetime] = None

    def refresh_abilities(self) -> None:
        self._ability_cache.clear()
        self._abilities_by_type.clear()
        self._model_cache.clear()

        for server in self.server_manager.list_servers():
            if not server.is_enabled:
                continue

            try:
                instances, models = self._discover_server_abilities(server)
                for instance in instances:
                    self._ability_cache[instance.key] = instance

                    if instance.ability_type not in self._abilities_by_type:
                        self._abilities_by_type[instance.ability_type] = []
                    self._abilities_by_type[instance.ability_type].append(instance.key)

                if models:
                    self._model_cache[server.name] = models

            except Exception as e:
                logger.error(f"Failed to discover abilities for server {server.name}: {e}")

        self._last_refresh = datetime.now()
        logger.info(f"Refreshed abilities: {len(self._ability_cache)} instances found")

    def _discover_server_abilities(self, server: Server) -> tuple:
        instances: List[AbilityInstance] = []
        models_by_ability: Dict[str, List[ModelInfo]] = {}
        config = server.config
        plugin_info = server.get_plugin_info()

        if not plugin_info:
            return instances, models_by_ability

        for abil in plugin_info.abilities:
            try:
                ability_type = Ability(abil.name)
            except ValueError:
                logger.warning(f"Unknown ability type: {abil.name}")
                continue

            model_infos = self._build_model_infos(config, ability_type, abil)
            models_by_ability[ability_type.value] = model_infos

            for model_info in model_infos:
                instance = AbilityInstance.from_model_info(config.name, model_info)
                instance.metadata.update({
                    "server_type": config.server_type,
                    "plugin_name": config.plugin_name,
                    "engine": plugin_info.engine,
                })
                instances.append(instance)

        return instances, models_by_ability

    def _build_model_infos(
        self,
        config,
        ability_type: Ability,
        ability_config,
    ) -> List[ModelInfo]:
        model_infos: List[ModelInfo] = []
        plugin_models = getattr(ability_config, "models", []) or []

        if plugin_models:
            for model_data in plugin_models:
                model_infos.append(
                    self._create_model_info(model_data, ability_type, config)
                )
        else:
            models = self._extract_models_for_ability(
                config, ability_type, ability_config.description
            )
            for model_name, model_info_dict in models.items():
                model_infos.append(
                    ModelInfo(
                        name=model_name,
                        display_name=model_info_dict.get("display_name", model_name),
                        description=model_info_dict.get(
                            "description", ability_config.description
                        ),
                        ability=ability_type,
                        provider=config.server_type,
                        tags=model_info_dict.get("tags", []),
                        specs=model_info_dict.get("specs", {}),
                        pricing=self._build_pricing(model_info_dict.get("pricing")),
                        is_default=model_info_dict.get("is_default", False),
                        is_available=model_info_dict.get("is_available", True),
                    )
                )

        return self._filter_model_infos_by_ability_models(
            config, ability_type, model_infos
        )

    def _filter_model_infos_by_ability_models(
        self,
        config,
        ability_type: Ability,
        model_infos: List[ModelInfo],
    ) -> List[ModelInfo]:
        ability = ability_type.value
        return [
            m
            for m in model_infos
            if is_model_enabled_for_ability(config.parameters, ability, m.name)
        ]

    def _create_model_info(
        self,
        model_data: Dict[str, Any],
        ability_type: Ability,
        config,
    ) -> ModelInfo:
        return ModelInfo(
            name=model_data.get("name", "default"),
            display_name=model_data.get(
                "display_name", model_data.get("name", "default")
            ),
            description=model_data.get("description", ""),
            ability=ability_type,
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

    def _build_pricing(
        self, pricing_data: Optional[Dict[str, Any]]
    ) -> Optional[ModelPricing]:
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

    def _extract_models_for_ability(
        self,
        config,
        ability_type: Ability,
        ability_description: str,
    ) -> Dict[str, Dict[str, Any]]:
        models: Dict[str, Dict[str, Any]] = {}
        raw_models = config.parameters.get("models")
        if isinstance(raw_models, dict):
            ability_models_config: Any = raw_models.get(ability_type.value, {})
        elif isinstance(raw_models, list):
            ability_models_config = raw_models
        else:
            ability_models_config = {}

        if isinstance(ability_models_config, list):
            for item in ability_models_config:
                if isinstance(item, str):
                    models[item] = {"description": f"Model {item}"}
                elif isinstance(item, dict) and "name" in item:
                    model_name = item.pop("name")
                    models[model_name] = item
        elif isinstance(ability_models_config, dict):
            models.update(ability_models_config)

        if not models:
            default_model = config.parameters.get("default_model")
            if default_model:
                models[default_model] = {
                    "description": f"Default model for {ability_type.value}",
                    "is_default": True,
                }
            else:
                models["default"] = {
                    "description": ability_description,
                    "is_default": True,
                }

        return models

    def get_all_ability_instances(self) -> List[AbilityInstance]:
        if not self._ability_cache:
            self.refresh_abilities()
        return list(self._ability_cache.values())

    def get_ability_instances_by_type(self, ability: Ability) -> List[AbilityInstance]:
        if not self._ability_cache:
            self.refresh_abilities()
        keys = self._abilities_by_type.get(ability, [])
        return [self._ability_cache[k] for k in keys if k in self._ability_cache]

    def get_ability_instance(self, key: str) -> Optional[AbilityInstance]:
        if not self._ability_cache:
            self.refresh_abilities()
        return self._ability_cache.get(key)

    def get_ability_groups(self) -> List[AbilityGroup]:
        if not self._ability_cache:
            self.refresh_abilities()
        groups: List[AbilityGroup] = []
        for ability in Ability:
            instances = self.get_ability_instances_by_type(ability)
            if not instances:
                continue
            models = self._aggregate_models_for_ability(ability)
            groups.append(
                AbilityGroup(
                    ability_type=ability,
                    ability_name=self.ABILITY_NAMES.get(ability, ability.value),
                    description=self.ABILITY_DESCRIPTIONS.get(ability, ""),
                    instances=instances,
                    models=models,
                )
            )
        return groups

    def _aggregate_models_for_ability(self, ability: Ability) -> List[ModelInfo]:
        models: List[ModelInfo] = []
        seen_names: set = set()
        name = ability.value
        for _server_name, ab_models in self._model_cache.items():
            if name in ab_models:
                for model_info in ab_models[name]:
                    if model_info.name not in seen_names:
                        seen_names.add(model_info.name)
                        models.append(model_info)
        return models

    def get_models_for_ability(self, ability: Ability) -> List[ModelInfo]:
        if not self._ability_cache:
            self.refresh_abilities()
        return self._aggregate_models_for_ability(ability)

    def get_ability_keys_by_type(self, ability: Ability) -> List[str]:
        instances = self.get_ability_instances_by_type(ability)
        return [inst.key for inst in instances]

    def get_llm_selection_context(
        self,
        ability: Ability,
        user_requirement: str = "",
    ) -> Dict[str, Any]:
        instances = self.get_ability_instances_by_type(ability)
        if not instances:
            return {
                "ability_type": ability.value,
                "available": False,
                "message": f"No available abilities for {ability.value}",
            }

        options = []
        for inst in instances:
            option: Dict[str, Any] = {
                "key": inst.key,
                "server": inst.server_name,
                "model": inst.model_name,
                "description": inst.description,
                "tags": inst.tags,
                "specs": inst.specs,
                "priority": inst.priority,
            }
            if inst.pricing:
                option["pricing"] = inst.pricing.to_dict()
            options.append(option)

        return {
            "ability_type": ability.value,
            "ability_name": self.ABILITY_NAMES.get(ability, ability.value),
            "available": True,
            "user_requirement": user_requirement,
            "options": options,
            "selection_hint": (
                "Select the most appropriate key based on user requirements, "
                "considering tags, specs, priority, and pricing."
            ),
        }
