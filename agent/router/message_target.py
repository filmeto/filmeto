"""
Message Target Module

Provides @mention-based routing target parsing for crew member responses.
Enables explicit routing decisions without LLM calls when targets are clear.
"""
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


# Sentinel token used to address the end-user directly.
YOU_TOKEN = "You"

# Hard cap on the number of @member mentions honoured per message.
MAX_MENTIONS = 10


class TargetType(Enum):
    USER = "user"           # @You - reply directly to user, end conversation
    MEMBER = "member"       # @MemberName - send to specific member(s)
    BROADCAST = "broadcast" # no valid @mention - use LLM routing


@dataclass
class MessageTarget:
    target_type: TargetType
    target_names: List[str] = field(default_factory=list)

    @classmethod
    def parse_from_content(cls, content: str, available_members: List[str]) -> "MessageTarget":
        """
        Parse routing target from message content.

        Rules (in priority order):
        1. Contains @You (exact word, case-insensitive) -> USER (terminates chain)
        2. Contains @MemberName for a known member -> MEMBER (direct route)
        3. No valid @mention -> BROADCAST (fall through to LLM routing)

        Member names are matched by building a pattern from the known member
        list, so names containing hyphens, dots, Unicode, etc. all work.
        @You takes priority over any @MemberName mention in the same message.

        Empty target_names with TargetType.MEMBER cannot occur: when no valid
        member is matched the method returns BROADCAST instead.
        """
        if not content:
            return cls(target_type=TargetType.BROADCAST)

        # 1. @You — must be followed by whitespace, punctuation, or end-of-string
        #    so @Youth / @YouTube are NOT matched.
        if re.search(r'@' + YOU_TOKEN + r'(?=[\s\.,;:!?\)\]\}]|$)', content, re.IGNORECASE):
            return cls(target_type=TargetType.USER)

        # 2. @MemberName — build pattern from known member names so that
        #    names with hyphens, dots, spaces, or Unicode work correctly.
        #    Sort by descending length to avoid short-name shadowing long ones.
        if not available_members:
            return cls(target_type=TargetType.BROADCAST)

        sorted_members = sorted(available_members, key=len, reverse=True)
        # Exclude "You" (case-insensitive) to avoid it being treated as a member name
        sorted_members = [m for m in sorted_members if m.lower() != YOU_TOKEN.lower()]

        member_pattern = '|'.join(re.escape(m) for m in sorted_members)
        # Member token must also end at a word boundary equivalent
        # Build boundary lookahead separately to avoid f-string brace escaping issues
        _boundary = r'(?=[\s\.,;:!?\)\]\}]|$)'
        pattern = r'@(' + member_pattern + r')' + _boundary

        mentioned: List[str] = []
        member_lower_map = {m.lower(): m for m in available_members}

        for match in re.finditer(pattern, content, re.IGNORECASE):
            name_lower = match.group(1).lower()
            actual = member_lower_map.get(name_lower)
            if actual and actual not in mentioned:
                mentioned.append(actual)
                if len(mentioned) >= MAX_MENTIONS:
                    break

        if mentioned:
            return cls(target_type=TargetType.MEMBER, target_names=mentioned)

        return cls(target_type=TargetType.BROADCAST)

    def is_terminal(self) -> bool:
        """True if this message ends the routing chain (sent directly to user)."""
        return self.target_type == TargetType.USER
