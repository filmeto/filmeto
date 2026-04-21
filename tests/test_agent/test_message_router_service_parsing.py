from agent.router.message_router_service import MessageRouterService


def test_parse_routing_response_supports_jsonl_and_excludes_sender() -> None:
    service = MessageRouterService(chat_service=object())
    crew_members = {"producer": object(), "writer": object(), "user": object()}
    content = (
        '{"crew_member":"producer","message":"m1"}\n'
        '{"crew_member":"writer","message":"m2"}\n'
        '{"crew_member":"user","message":"self"}'
    )

    decision = service._parse_routing_response(content, crew_members, sender_id="user")
    assert decision.routed_members == ["producer", "writer"]
    assert decision.member_messages == {"producer": "m1", "writer": "m2"}


def test_parse_routing_response_supports_legacy_format() -> None:
    service = MessageRouterService(chat_service=object())
    crew_members = {"Producer": object(), "writer": object()}
    content = (
        '{"routed_members":["producer"],'
        '"member_messages":{"producer":"please handle this"}}'
    )
    decision = service._parse_routing_response(content, crew_members, sender_id="user")
    assert decision.routed_members == ["Producer"]
    assert decision.member_messages == {"Producer": "please handle this"}


def test_fallback_routing_prefers_producer_then_first_non_sender() -> None:
    service = MessageRouterService(chat_service=object())
    decision_with_producer = service._fallback_routing(
        "hi", sender_id="user", crew_members={"producer": object(), "writer": object()}
    )
    decision_without_producer = service._fallback_routing(
        "hi", sender_id="writer", crew_members={"writer": object(), "editor": object()}
    )
    assert decision_with_producer.routed_members == ["producer"]
    assert decision_without_producer.routed_members == ["editor"]
