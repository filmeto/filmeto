from agent.router.message_target import MAX_MENTIONS, MessageTarget, TargetType


def test_parse_user_target_has_priority_over_members() -> None:
    target = MessageTarget.parse_from_content(
        "Please check this @producer and also @You",
        available_members=["producer", "writer"],
    )
    assert target.target_type == TargetType.USER
    assert target.target_names == []


def test_parse_member_mentions_preserves_known_names() -> None:
    target = MessageTarget.parse_from_content(
        "@ScreenWriter please work with @producer",
        available_members=["screenwriter", "producer"],
    )
    assert target.target_type == TargetType.MEMBER
    assert target.target_names == ["screenwriter", "producer"]


def test_parse_member_mentions_caps_at_max_mentions() -> None:
    members = [f"m{i}" for i in range(MAX_MENTIONS + 5)]
    content = " ".join([f"@{name}" for name in members])
    target = MessageTarget.parse_from_content(content, available_members=members)
    assert target.target_type == TargetType.MEMBER
    assert len(target.target_names) == MAX_MENTIONS


def test_parse_broadcast_when_no_valid_mentions() -> None:
    target = MessageTarget.parse_from_content(
        "hello @unknown",
        available_members=["producer"],
    )
    assert target.target_type == TargetType.BROADCAST
    assert not target.is_terminal()
