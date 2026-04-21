from agent.react.actions import FinalAction, ToolAction
from agent.react.constants import StopReason
from agent.react.parser import ReactActionParser


def test_parse_tool_action_with_aliases_and_invalid_args_fallback() -> None:
    action = ReactActionParser.parse(
        response_text="ignored",
        payload={
            "action": "tool",
            "name": "timeline_item",
            "arguments": "not-a-dict",
            "thought": "thinking",
        },
    )
    assert isinstance(action, ToolAction)
    assert action.tool_name == "timeline_item"
    assert action.tool_args == {}
    assert action.thinking == "thinking"


def test_parse_no_json_falls_back_to_final_and_extracts_mention() -> None:
    action = ReactActionParser.parse("@You please confirm")
    assert isinstance(action, FinalAction)
    assert action.final == "@You please confirm"
    assert action.stop_reason == StopReason.NO_JSON.value
    assert action.speak_to == "You"


def test_parse_unknown_type_defaults_to_final_action() -> None:
    action = ReactActionParser.parse(
        response_text="fallback text",
        payload={"type": "mystery", "answer": "done"},
    )
    assert isinstance(action, FinalAction)
    assert action.final == "done"
    assert action.stop_reason == StopReason.UNKNOWN_TYPE.value


def test_get_tool_result_payload_formats_success_and_error() -> None:
    ok_payload = ReactActionParser.get_tool_result_payload("todo", result={"a": 1}, ok=True)
    err_payload = ReactActionParser.get_tool_result_payload("todo", ok=False, error="boom")
    assert ok_payload == {"tool_name": "todo", "ok": True, "result": {"a": 1}}
    assert err_payload == {"tool_name": "todo", "ok": False, "error": "boom"}
