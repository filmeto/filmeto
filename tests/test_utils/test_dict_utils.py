from utils.dict_utils import get_value, set_value


def test_get_value_returns_default_for_none() -> None:
    assert get_value(None, "k", "fallback") == "fallback"


def test_get_value_reads_existing_key() -> None:
    assert get_value({"k": 1}, "k", 0) == 1


def test_set_value_updates_dict_in_place() -> None:
    payload = {}
    set_value(payload, "k", 2)
    assert payload["k"] == 2
