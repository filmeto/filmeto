"""
Test SkillChat React instance isolation.

Tests that:
1. React instances are properly isolated by crew_member and conversation_id
2. react_type includes skill_name, crew_member_name, and conversation_id
3. Checkpoints don't pollute between different conversations/crew members
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.skill.skill_models import Skill
from agent.skill.skill_chat import SkillChat
from agent.skill.skill_service import SkillService


class MockSkillService:
    """Mock skill service for testing."""

    def execute_script(self, script_path, argv, context, **kwargs):
        """Mock script execution."""
        return {"result": f"Executed {script_path} with args {argv}"}


class TestSkillChatReactIsolation:
    """Tests for React instance isolation in SkillChat."""

    def test_react_type_includes_crew_member_and_conversation(self):
        """Test that react_type includes skill_name, crew_member_name, and conversation_id."""
        from agent.skill.skill_chat import SkillChat
        import asyncio

        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/test/path"
        )

        skill_chat = SkillChat(skill_service=MockSkillService())

        # Test with crew_member_name and conversation_id
        async def test_with_params():
            events = []
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test message",
                workspace=None,
                project="test_project",
                crew_member_name="TestCrew",
                conversation_id="conv_123",
                max_steps=1,
            ):
                events.append(event)
                if len(events) > 2:
                    break

            # Check that react_type includes all parts
            for event in events:
                if hasattr(event, 'react_type') and event.react_type:
                    # Format should be: skill_{skill_name}_{crew_member}_{conversation_id}
                    # Note: skill_name may contain underscores, so we check if react_type starts with "skill_{skill_name}_"
                    assert event.react_type.startswith(f"skill_{skill.name}_")
                    assert "testcrew" in event.react_type.lower()
                    assert "conv_123" in event.react_type
                    # Verify the crew_member and conversation_id are present after the skill prefix
                    after_skill = event.react_type[len(f"skill_{skill.name}_"):]
                    assert "testcrew" in after_skill.lower()
                    assert "conv_123" in after_skill

        asyncio.run(test_with_params())

    def test_different_crew_members_have_different_react_types(self):
        """Test that different crew members get different react_types for same skill."""
        from agent.skill.skill_chat import SkillChat
        import asyncio

        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/test/path"
        )

        skill_chat = SkillChat(skill_service=MockSkillService())

        async def test_different_crew():
            react_types = []

            # Crew 1
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                crew_member_name="CrewMember1",
                conversation_id="conv_123",
                max_steps=1,
            ):
                if event.react_type:
                    react_types.append(("crew1", event.react_type))
                break

            # Crew 2 with same conversation
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                crew_member_name="CrewMember2",
                conversation_id="conv_123",
                max_steps=1,
            ):
                if event.react_type:
                    react_types.append(("crew2", event.react_type))
                break

            # Verify react_types are different
            assert len(react_types) == 2
            type1 = react_types[0][1]
            type2 = react_types[1][1]
            assert type1 != type2
            # Both should have same skill and conversation, but different crew member
            assert "crewmember1" in type1.lower()
            assert "crewmember2" in type2.lower()
            assert "conv_123" in type1
            assert "conv_123" in type2

        asyncio.run(test_different_crew())

    def test_different_conversations_have_different_react_types(self):
        """Test that different conversations get different react_types."""
        from agent.skill.skill_chat import SkillChat
        import asyncio

        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/test/path"
        )

        skill_chat = SkillChat(skill_service=MockSkillService())

        async def test_different_convs():
            react_types = []

            # Conversation 1
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                crew_member_name="CrewMember1",
                conversation_id="conv_001",
                max_steps=1,
            ):
                if event.react_type:
                    react_types.append(("conv1", event.react_type))
                break

            # Conversation 2 with same crew member
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                crew_member_name="CrewMember1",
                conversation_id="conv_002",
                max_steps=1,
            ):
                if event.react_type:
                    react_types.append(("conv2", event.react_type))
                break

            # Verify react_types are different
            assert len(react_types) == 2
            type1 = react_types[0][1]
            type2 = react_types[1][1]
            assert type1 != type2
            # Both should have same skill and crew member, but different conversation
            assert "conv_001" in type1
            assert "conv_002" in type2

        asyncio.run(test_different_convs())

    def test_auto_generate_conversation_id_when_not_provided(self):
        """Test that conversation_id is auto-generated when not provided."""
        from agent.skill.skill_chat import SkillChat
        import asyncio

        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/test/path"
        )

        skill_chat = SkillChat(skill_service=MockSkillService())

        async def test_auto_generate():
            react_types = []

            # Call without conversation_id
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                crew_member_name="TestCrew",
                conversation_id=None,  # Not provided
                max_steps=1,
            ):
                if event.react_type:
                    react_types.append(event.react_type)
                break

            # Should still have a unique react_type with generated conversation part
            assert len(react_types) == 1
            react_type = react_types[0]
            # Should contain conv_{run_id} format
            assert "test_skill" in react_type
            assert "testcrew" in react_type.lower()
            assert "conv_" in react_type

        asyncio.run(test_auto_generate())

    def test_backward_compatibility_without_new_params(self):
        """Test that code works without new parameters (backward compatibility)."""
        from agent.skill.skill_chat import SkillChat
        import asyncio

        skill = Skill(
            name="test_skill",
            description="Test skill",
            knowledge="Test knowledge",
            skill_path="/test/path"
        )

        skill_chat = SkillChat(skill_service=MockSkillService())

        async def test_backward_compat():
            # Call without crew_member_name and conversation_id
            async for event in skill_chat.chat_stream(
                skill=skill,
                user_message="Test",
                workspace=None,
                project="test_project",
                # crew_member_name not provided
                # conversation_id not provided
                max_steps=1,
            ):
                # Should still work with defaults
                assert event is not None
                if event.react_type:
                    # Should have default parts
                    assert "test_skill" in event.react_type
                break

        asyncio.run(test_backward_compat())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
