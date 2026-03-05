"""
Message Router Service Module

Provides intelligent message routing for multi-crew member group chats.
Uses LLM to analyze conversation context and route messages to appropriate crew members.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from agent.llm.llm_service import LlmService
from agent.prompt.prompt_service import prompt_service
from utils.i18n_utils import translation_manager

if TYPE_CHECKING:
    from agent.crew.crew_member import CrewMember

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """
    Represents the routing decision for a message.

    Attributes:
        routed_members: List of crew member names that should respond
        member_messages: Dict mapping crew member name to customized message
    """
    routed_members: List[str] = field(default_factory=list)
    member_messages: Dict[str, str] = field(default_factory=dict)


class MessageRouterService:
    """
    Service for routing messages to appropriate crew members using LLM.

    This service analyzes incoming messages along with conversation context
    and crew member capabilities to determine which crew members should respond
    and how to customize the message for each recipient.
    """

    def __init__(self, llm_service: Optional[LlmService] = None, workspace: Any = None):
        """
        Initialize the MessageRouterService.

        Args:
            llm_service: Optional LLM service for routing decisions
            workspace: Optional workspace for LLM service initialization
        """
        self.llm_service = llm_service or LlmService(workspace)

    async def route_message(
        self,
        message: str,
        sender_id: str,
        sender_name: str,
        crew_members: Dict[str, "CrewMember"],
        conversation_history: List[Dict],
        max_history: int = 20,
    ) -> RoutingDecision:
        """
        Route a message to appropriate crew members using LLM analysis.

        Args:
            message: The message to route
            sender_id: ID of the message sender
            sender_name: Display name of the sender
            crew_members: Dict of available crew members (name -> CrewMember)
            conversation_history: Recent conversation history
            max_history: Maximum number of history items to include

        Returns:
            RoutingDecision with routed members and customized messages
        """
        if not crew_members:
            logger.warning("No crew members available for routing")
            return RoutingDecision(
                routed_members=[],
                member_messages={},
            )

        # Validate LLM service
        if not self.llm_service or not self.llm_service.validate_config():
            logger.warning("LLM service not configured, using fallback routing")
            return self._fallback_routing(message, sender_id, crew_members)

        try:
            # Build the routing prompt
            prompt = self._build_routing_prompt(
                message=message,
                sender_id=sender_id,
                sender_name=sender_name,
                crew_members=crew_members,
                conversation_history=conversation_history[-max_history:] if conversation_history else [],
            )

            # Call LLM for routing decision
            response = await self.llm_service.acompletion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temperature for more consistent routing
            )

            # Extract content from response
            content = LlmService.extract_content(response)
            if not content:
                logger.warning("Empty LLM response for routing")
                return self._fallback_routing(message, sender_id, crew_members)

            # Parse the routing decision
            decision = self._parse_routing_response(content, crew_members, sender_id)
            logger.info(f"LLM routing decision: {decision.routed_members}")
            return decision

        except Exception as e:
            logger.error(f"Error in LLM routing: {e}", exc_info=True)
            return self._fallback_routing(message, sender_id, crew_members)

    def _build_routing_prompt(
        self,
        message: str,
        sender_id: str,
        sender_name: str,
        crew_members: Dict[str, "CrewMember"],
        conversation_history: List[Dict],
    ) -> str:
        """
        Build the prompt for the routing LLM call.

        Args:
            message: The message to route
            sender_id: ID of the sender
            sender_name: Display name of the sender
            crew_members: Available crew members
            conversation_history: Recent conversation history

        Returns:
            Formatted prompt string
        """
        # Get current language
        language = translation_manager.get_current_language()

        # Build crew members info
        crew_info_list = []
        for name, member in crew_members.items():
            # Skip the sender from being a routing target
            if name.lower() == sender_id.lower():
                continue

            crew_title = member.config.metadata.get('crew_title', name) if member.config.metadata else name
            skills = ", ".join(member.config.skills) if member.config.skills else "None"
            description = member.config.description or "No description"

            crew_info_list.append({
                "name": name,
                "crew_title": crew_title,
                "description": description,
                "skills": skills,
            })

        # Build conversation history string
        history_str = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history:
                role = msg.get("role", "unknown")
                sender = msg.get("sender_id", msg.get("sender_name", role))
                content = msg.get("content", "")
                if content:
                    # Truncate long messages
                    if len(content) > 200:
                        content = content[:197] + "..."
                    history_lines.append(f"[{sender}]: {content}")
            history_str = "\n".join(history_lines)

        # Use prompt service to render the template
        rendered_prompt = prompt_service.render_prompt(
            name="message_router",
            language=language,
            sender_id=sender_id,
            sender_name=sender_name,
            message=message,
            crew_members_info=json.dumps(crew_info_list, ensure_ascii=False, indent=2),
            conversation_history=history_str,
        )

        if rendered_prompt:
            return rendered_prompt

        # Fallback prompt if template not found
        return self._build_fallback_prompt(
            message, sender_id, sender_name, crew_info_list, history_str
        )

    def _build_fallback_prompt(
        self,
        message: str,
        sender_id: str,
        sender_name: str,
        crew_info_list: List[Dict],
        history_str: str,
    ) -> str:
        """Build a fallback prompt if the template is not available."""
        crew_info_str = json.dumps(crew_info_list, ensure_ascii=False, indent=2)

        return f"""You are a message router for a multi-agent group chat system.

## Current Sender
- ID: {sender_id}
- Name: {sender_name}

## Message to Route
{message}

## Available Crew Members
{crew_info_str}

## Recent Conversation History
{history_str if history_str else 'No recent history'}

## Routing Rules
1. Analyze the message and determine which crew members should respond
2. Consider each member's role, skills, and description
3. Multiple members can be selected if the message requires collaboration
4. Don't route to the sender
5. If no specific member is needed, route to "producer" if available

Respond ONLY with JSONL format (one JSON object per line, no markdown code blocks):
{"crew_member": "member_name", "message": "customized message for this member"}

Example for routing to two members:
{"crew_member": "translator", "message": "Please translate this..."}
{"crew_member": "editor", "message": "Please edit this..."}

Respond ONLY with the JSONL lines, no other text."""

    def _parse_routing_response(
        self,
        content: str,
        crew_members: Dict[str, "CrewMember"],
        sender_id: str,
    ) -> RoutingDecision:
        """
        Parse the LLM response into a RoutingDecision.
        Expects JSONL format with each line containing:
        {"crew_member": "name", "message": "customized message"}

        Args:
            content: Raw LLM response content (JSONL lines)
            crew_members: Available crew members for validation
            sender_id: ID of the sender (to exclude from routing)

        Returns:
            Parsed RoutingDecision
        """
        valid_members = []
        valid_messages = {}

        try:
            # Try JSONL format first - each line is a JSON object
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]

            # Check if it's JSONL format (multiple lines) or single JSON object
            if len(lines) > 1:
                # JSONL format
                for line in lines:
                    data = json.loads(line)
                    member_name = data.get("crew_member")
                    message = data.get("message", "")

                    if not member_name:
                        continue

                    actual_name = self._find_member_name(member_name, crew_members)
                    if actual_name and actual_name.lower() != sender_id.lower():
                        valid_members.append(actual_name)
                        if message:
                            valid_messages[actual_name] = message
            else:
                # Single JSON object - try new format first, then legacy format
                data = json.loads(lines[0]) if lines else {}

                # Try new JSONL format (single item)
                if "crew_member" in data:
                    member_name = data.get("crew_member")
                    message = data.get("message", "")

                    actual_name = self._find_member_name(member_name, crew_members)
                    if actual_name and actual_name.lower() != sender_id.lower():
                        valid_members.append(actual_name)
                        if message:
                            valid_messages[actual_name] = message
                # Legacy JSON format
                elif "routed_members" in data:
                    member_messages = data.get("member_messages", {})
                    for member_name in data.get("routed_members", []):
                        actual_name = self._find_member_name(member_name, crew_members)
                        if actual_name and actual_name.lower() != sender_id.lower():
                            valid_members.append(actual_name)
                            customized_msg = member_messages.get(member_name, member_messages.get(actual_name))
                            if customized_msg:
                                valid_messages[actual_name] = customized_msg

            return RoutingDecision(
                routed_members=valid_members,
                member_messages=valid_messages,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in routing response: {e}")
            return RoutingDecision(
                routed_members=[],
                member_messages={},
            )
        except Exception as e:
            logger.error(f"Error parsing routing response: {e}", exc_info=True)
            return RoutingDecision(
                routed_members=[],
                member_messages={},
            )

    def _find_member_name(self, member_name: str, crew_members: Dict[str, "CrewMember"]) -> Optional[str]:
        """
        Find the actual member name using case-insensitive comparison.

        Args:
            member_name: The member name to look up
            crew_members: Available crew members dict

        Returns:
            The actual member name or None if not found
        """
        for name in crew_members:
            if name.lower() == member_name.lower():
                return name
        return None

    def _fallback_routing(
        self,
        message: str,
        sender_id: str,
        crew_members: Dict[str, "CrewMember"],
    ) -> RoutingDecision:
        """
        Fallback routing when LLM is not available.

        Routes to producer if available, otherwise to the first available member.

        Args:
            message: The message to route
            sender_id: ID of the sender
            crew_members: Available crew members

        Returns:
            RoutingDecision with fallback routing
        """
        # Try to find producer
        producer_name = None
        for name in crew_members:
            if name.lower() == "producer":
                producer_name = name
                break

        if producer_name and producer_name.lower() != sender_id.lower():
            return RoutingDecision(
                routed_members=[producer_name],
                member_messages={producer_name: message},
            )

        # Find first available member that's not the sender
        for name in crew_members:
            if name.lower() != sender_id.lower():
                return RoutingDecision(
                    routed_members=[name],
                    member_messages={name: message},
                )

        return RoutingDecision(
            routed_members=[],
            member_messages={},
        )


# Singleton instance
message_router_service = MessageRouterService()
