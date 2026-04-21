import pytest

from server.api.types import Ability, AbilityInstance, SelectionConfig, SelectionMode
from server.service.ability_selection_service import AbilitySelectionService, SelectionError


class _FakeAbilityService:
    def __init__(self, instances):
        self._instances = instances
        self.refreshed = False

    def refresh_abilities(self):
        self.refreshed = True

    def get_ability_instances_by_type(self, _ability):
        return list(self._instances)

    def get_ability_instance(self, key):
        for inst in self._instances:
            if inst.key == key:
                return inst
        return None


def _make_instance(key, priority, tags=None, model="m", server="s"):
    return AbilityInstance(
        key=key,
        server_name=server,
        model_name=model,
        ability_type=Ability.TEXT2IMAGE,
        description="d",
        priority=priority,
        tags=tags or [],
    )


def test_select_auto_picks_highest_priority():
    service = AbilitySelectionService(server_manager=object())
    service._ability_service = _FakeAbilityService(
        [
            _make_instance("s:a", priority=1, model="a"),
            _make_instance("s:b", priority=9, model="b"),
        ]
    )

    result = service.select(Ability.TEXT2IMAGE, SelectionConfig.auto())

    assert result.mode_used == SelectionMode.AUTO
    assert result.model_name == "b"
    assert result.candidates_count == 2


def test_select_server_only_filters_by_server_and_tags():
    service = AbilitySelectionService(server_manager=object())
    service._ability_service = _FakeAbilityService(
        [
            _make_instance("a:m1", priority=3, tags=["fast"], model="m1", server="a"),
            _make_instance("b:m2", priority=8, tags=["fast"], model="m2", server="b"),
            _make_instance("a:m3", priority=10, tags=["quality"], model="m3", server="a"),
        ]
    )

    config = SelectionConfig.server_only("a", tags=["fast"])
    result = service.select(Ability.TEXT2IMAGE, config)

    assert result.server_name == "a"
    assert result.model_name == "m1"


def test_select_exact_requires_available_matching_instance():
    service = AbilitySelectionService(server_manager=object())
    inst = _make_instance("srv:model", priority=5, model="model", server="srv")
    inst.is_available = False
    service._ability_service = _FakeAbilityService([inst])

    with pytest.raises(SelectionError):
        service.select(Ability.TEXT2IMAGE, SelectionConfig.exact("srv", "model"))
