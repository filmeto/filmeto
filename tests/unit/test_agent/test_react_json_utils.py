from agent.react.json_utils import JsonExtractor


def test_extract_json_from_plain_object() -> None:
    payload = JsonExtractor.extract_json('{"type":"final","final":"ok"}')
    assert payload == {"type": "final", "final": "ok"}


def test_extract_json_from_markdown_code_block() -> None:
    text = "prefix\n```json\n{\"type\":\"tool\",\"tool_name\":\"x\"}\n```\nsuffix"
    payload = JsonExtractor.extract_json(text)
    assert payload == {"type": "tool", "tool_name": "x"}


def test_extract_code_block_content_strict_mode_requires_json_tag() -> None:
    content = JsonExtractor.extract_code_block_content("```python\nprint(1)\n```", strict=True)
    assert content is None


def test_find_balanced_json_returns_first_object() -> None:
    text = 'noise {"a":{"b":1}} trailing {"c":2}'
    found = JsonExtractor.find_balanced_json(text)
    assert found == '{"a":{"b":1}}'
