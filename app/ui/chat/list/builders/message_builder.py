"""Message builder for constructing chat list items from history data.

This module handles building QML-compatible chat list items from
various data sources including history storage and real-time events.
"""

import copy
import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from agent.chat.agent_chat_message import AgentMessage as ChatAgentMessage
from agent.chat.agent_chat_types import ContentType
from agent.chat.content import StructureContent

from app.ui.chat.list.agent_chat_list_items import ChatListItem

if TYPE_CHECKING:
    from app.ui.chat.list.managers.metadata_resolver import MetadataResolver
    from app.ui.chat.list.agent_chat_list_model import QmlAgentChatListModel

logger = logging.getLogger(__name__)


class MessageBuilder:
    """Builds chat list items from history data and handles content merging.

    This class is the SINGLE SOURCE OF TRUTH for message grouping and merging logic.
    All message combination logic should be centralized here to ensure consistency
    between history loading and real-time streaming.

    This class handles:
    - Grouping raw messages by message_id with smart deduplication
    - Converting history data to ChatListItem objects
    - Merging skill content entries
    - Merging content into existing message bubbles
    - Skill state priority handling
    - Metadata deduplication by event_type

    Attributes:
        _metadata_resolver: Resolver for crew member metadata
        _model: QML model instance for accessing constants
    """

    def __init__(
        self,
        metadata_resolver: "MetadataResolver",
        model: "QmlAgentChatListModel"
    ):
        """Initialize the message builder.

        Args:
            metadata_resolver: Resolver for crew member metadata
            model: QML model instance
        """
        self._metadata_resolver = metadata_resolver
        self._model = model
        self._skill_state_priority: Optional[Dict[str, int]] = None

    @staticmethod
    def _copy_content_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """Return an independent copy of a content item dict.

        Used when appending content to merged lists so the model owns its data.
        Single-item deepcopy is kept here; bulk copies are avoided elsewhere.
        """
        return copy.deepcopy(item)

    def _resolve_crew_read_by(
        self, raw_crew_members: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Enrich crew_read_by list with icon/color from metadata for display.

        History may store minimal entries (e.g. name only). Ensure each entry
        has id, name, icon, color for QML bubble display.
        """
        if not raw_crew_members:
            return []
        if not self._metadata_resolver._crew_member_metadata:
            self._metadata_resolver.load_crew_member_metadata()
        result = []
        for m in raw_crew_members:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or m.get("id") or ""
            if not name:
                continue
            key = name.lower()
            crew = self._metadata_resolver._crew_member_metadata.get(key)
            if crew:
                result.append({
                    "id": crew.config.name.lower(),
                    "name": crew.config.name,
                    "icon": getattr(crew.config, "icon", "🤖"),
                    "color": getattr(crew.config, "color", "#4a90e2"),
                })
            else:
                result.append({
                    "id": key,
                    "name": name,
                    "icon": m.get("icon", "🤖"),
                    "color": m.get("color", "#4a90e2"),
                })
        return result

    def build_items_from_raw_messages(
        self, raw_messages: List[Dict[str, Any]]
    ) -> List[ChatListItem]:
        """Build chat list items from raw storage messages.

        This is the PRIMARY method for loading messages from storage.
        It handles grouping by message_id and smart deduplication.

        Storage layer returns raw messages as stored (no merging).
        This method handles ALL grouping and merging logic to ensure
        consistency between history loading and real-time streaming.

        Args:
            raw_messages: List of raw message dictionaries from storage

        Returns:
            List of ChatListItem objects in chronological order (oldest first)
        """
        # Group messages by message_id with GSN tracking
        message_groups: Dict[str, Dict[str, Any]] = {}
        # Track content_id -> GSN mapping for deduplication
        content_gsn_map: Dict[str, int] = {}

        for msg_data in raw_messages:
            message_id = msg_data.get("message_id") or msg_data.get("metadata", {}).get("message_id", "")
            if not message_id:
                continue

            # Get GSN for this message
            msg_gsn = msg_data.get("metadata", {}).get("gsn", 0)

            # Initialize group if needed
            if message_id not in message_groups:
                message_groups[message_id] = {
                    "base": msg_data,
                    "content_items": [],
                    "max_gsn": msg_gsn
                }
            else:
                group = message_groups[message_id]
                # Prefer message with text content as base (not crew_member_read only)
                # crew_member_read may have same sender_id as user message
                current_base_type = (group["base"].get("message_type") or "")
                new_type = (msg_data.get("message_type") or "")
                if new_type == "text" and current_base_type != "text":
                    group["base"] = msg_data
                # Update max GSN
                if msg_gsn > group["max_gsn"]:
                    group["max_gsn"] = msg_gsn

            # Track content_id -> GSN mapping
            content_list = msg_data.get("content", [])
            for content_item in content_list:
                if isinstance(content_item, dict):
                    content_id = content_item.get("content_id")
                    if content_id and msg_gsn > content_gsn_map.get(content_id, 0):
                        content_gsn_map[content_id] = msg_gsn

            # Collect content items
            message_groups[message_id]["content_items"].extend(content_list)

        # Build items from grouped messages with deduplication
        items = []
        for message_id, group_data in message_groups.items():
            logger.debug(f"Building item for message_id: {message_id[:8]}, content_items count: {len(group_data['content_items'])}")

            # Apply smart deduplication
            deduplicated_content = self._deduplicate_content_items(
                group_data["content_items"],
                content_gsn_map
            )

            # Create combined message
            combined_msg = dict(group_data["base"])
            combined_msg["content"] = deduplicated_content

            logger.debug(f"  Combined content count: {len(deduplicated_content)}, types: {[c.get('content_type') for c in deduplicated_content if isinstance(c, dict)]}")

            # Build item from combined message
            item = self.build_item_from_history(combined_msg)
            if item:
                items.append(item)

        # Sort by max GSN to get chronological order
        items.sort(key=lambda item: self._extract_item_gsn(item))
        return items

    def _deduplicate_content_items(
        self,
        content_items: List[Dict[str, Any]],
        content_gsn_map: Dict[str, int]
    ) -> List[Dict[str, Any]]:
        """Deduplicate content items by content_id, keeping the highest GSN version.

        Single pass to build by content_id; one sort for chronological order.
        For metadata content, we use deterministic content_id. When multiple
        entries have the same content_id, we keep one (content_gsn_map already
        has max GSN per id from grouping).

        Args:
            content_items: List of content items to deduplicate
            content_gsn_map: Mapping of content_id to highest GSN

        Returns:
            Deduplicated list of content items with highest GSN for each content_id
        """
        by_id: Dict[str, Dict[str, Any]] = {}
        no_id_list: List[Dict[str, Any]] = []
        non_dict_items: List[Any] = []

        for item in content_items:
            if not isinstance(item, dict):
                non_dict_items.append(item)
                continue
            content_id = item.get("content_id", "") or ""
            if content_id:
                by_id[content_id] = item
            else:
                no_id_list.append(item)

        # Single sort: chronological (ascending GSN); no-id items get 0 and sort first
        to_sort = list(by_id.values()) + no_id_list
        to_sort.sort(key=lambda x: content_gsn_map.get(x.get("content_id", ""), 0))
        return to_sort + non_dict_items

    def _extract_item_gsn(self, item: ChatListItem) -> int:
        """Extract GSN from a ChatListItem for sorting.

        Args:
            item: ChatListItem to extract GSN from

        Returns:
            GSN value (0 if not found)
        """
        # First try to get GSN from item.metadata (works for both user and agent)
        if item.metadata:
            return item.metadata.get("gsn", 0)
        # For agent messages, also check agent_message.metadata
        if item.agent_message and item.agent_message.metadata:
            return item.agent_message.metadata.get("gsn", 0)
        return 0

    def build_item_from_history(self, msg_data: Dict[str, Any]) -> Optional[ChatListItem]:
        """Build a ChatListItem from history data.

        History JSON has fields at both top-level and in metadata.
        We check top-level first, then fallback to metadata.

        Args:
            msg_data: Message data dictionary from history

        Returns:
            ChatListItem or None if building fails
        """
        try:
            metadata = msg_data.get("metadata", {})
            content_list = msg_data.get("content", [])

            # Check both top-level and metadata for fields (top-level takes precedence)
            message_id = msg_data.get("message_id") or metadata.get("message_id", "")
            sender_id = msg_data.get("sender_id") or metadata.get("sender_id", "unknown")
            sender_name = msg_data.get("sender_name") or metadata.get("sender_name", sender_id)
            timestamp = msg_data.get("timestamp") or metadata.get("timestamp")

            if not message_id:
                logger.warning(f"No message_id in msg_data: {msg_data.keys()}")
                return None

            logger.debug(f"Parsing message: {message_id[:8]}... from {sender_name}")

            is_user = sender_id.lower() == "user"

            if is_user:
                text_content = ""
                crew_read_by = []
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        content_type = content_item.get("content_type")
                        if content_type == "text":
                            text_content = content_item.get("data", {}).get("text", "")
                        elif content_type == "crew_member_read":
                            # Extract crew_member_read for crew_read_by display
                            raw_crew_members = content_item.get("data", {}).get("crew_members", [])
                            logger.debug(f"  Found crew_member_read: {raw_crew_members}")
                            crew_read_by = self._resolve_crew_read_by(raw_crew_members)
                            logger.debug(f"  Resolved crew_read_by: {crew_read_by}")

                # Add timestamp to metadata for QML
                if timestamp and "timestamp" not in metadata:
                    metadata["timestamp"] = timestamp

                logger.debug(f"  User message: {text_content[:50]}..., crew_read_by count: {len(crew_read_by)}")
                return ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=True,
                    user_content=text_content,
                    metadata=metadata,  # Preserve metadata for GSN sorting and timestamp
                    crew_read_by=crew_read_by,
                )
            else:
                structured_content = []
                # Track skills by name for merging
                skills_by_name: Dict[str, List[Dict[str, Any]]] = {}
                # Position of first occurrence of each skill in the content stream
                skill_first_positions: Dict[str, int] = {}
                # Child content collected via _skill_name metadata marking
                skill_child_contents: Dict[str, List[Dict[str, Any]]] = {}
                # Unassociated tool_call entries
                tool_entries: List[Dict[str, Any]] = []
                # Track typing content - only keep the last one (should be END state)
                last_typing_content: Optional[Dict[str, Any]] = None
                # Extract crew_member_read for crew_read_by display
                crew_read_by = []
                for content_item in content_list:
                    if isinstance(content_item, dict) and content_item.get("content_type") == "crew_member_read":
                        raw_crew_members = content_item.get("data", {}).get("crew_members", [])
                        logger.debug(f"  Found crew_member_read for agent: {raw_crew_members}")
                        crew_read_by = self._resolve_crew_read_by(raw_crew_members)
                        break

                position = 0
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        content_type = content_item.get("content_type")
                        item_metadata = content_item.get("metadata")
                        skill_ref = (item_metadata.get("_skill_name")
                                     if isinstance(item_metadata, dict) else None)

                        # Special handling for typing content: only keep the last one
                        if content_type == "typing":
                            last_typing_content = content_item
                            continue  # Don't process now, handle after the loop
                        elif content_type == "skill":
                            skill_name = content_item.get("data", {}).get("skill_name", "")
                            if skill_name:
                                if skill_name not in skills_by_name:
                                    skills_by_name[skill_name] = []
                                    skill_first_positions[skill_name] = position
                                skills_by_name[skill_name].append(content_item)
                            else:
                                try:
                                    sc = StructureContent.from_dict(content_item)
                                    structured_content.append(sc)
                                    position += 1
                                except Exception as e:
                                    logger.debug(f"Failed to load structured content: {e}")
                        elif skill_ref:
                            # Content belongs to a skill (marked via metadata)
                            if skill_ref not in skill_child_contents:
                                skill_child_contents[skill_ref] = []
                            skill_child_contents[skill_ref].append(content_item)
                        elif content_type == "tool_call":
                            tool_entries.append(content_item)
                        else:
                            try:
                                sc = StructureContent.from_dict(content_item)
                                structured_content.append(sc)
                                position += 1
                            except Exception as e:
                                logger.debug(f"Failed to load structured content: {e}")

                # Merge skill entries and insert at the original position
                skill_inserts: List[tuple] = []
                for skill_name, skill_entries in skills_by_name.items():
                    extra_children = skill_child_contents.pop(skill_name, [])
                    merged_skill = self.merge_skill_entries(
                        skill_name, skill_entries, tool_entries,
                        extra_child_contents=extra_children,
                    )
                    if merged_skill:
                        insert_pos = skill_first_positions.get(
                            skill_name, len(structured_content))
                        skill_inserts.append((insert_pos, merged_skill))

                skill_inserts.sort(key=lambda x: x[0])
                for offset, (pos, merged_skill) in enumerate(skill_inserts):
                    structured_content.insert(pos + offset, merged_skill)

                # Any remaining skill_child_contents without a matching skill
                # are added as standalone content
                for orphan_children in skill_child_contents.values():
                    for child in orphan_children:
                        try:
                            sc = StructureContent.from_dict(child)
                            structured_content.append(sc)
                        except Exception as e:
                            logger.debug(f"Failed to load orphan child content: {e}")

                # Add the last typing content (should be END state) if any
                # This ensures only one typing indicator exists, preventing isStreaming=true
                if last_typing_content:
                    try:
                        typing_sc = StructureContent.from_dict(last_typing_content)
                        structured_content.append(typing_sc)
                    except Exception as e:
                        logger.debug(f"Failed to load typing content: {e}")

                # Add timestamp to metadata for QML
                if timestamp and "timestamp" not in metadata:
                    metadata["timestamp"] = timestamp

                agent_message = ChatAgentMessage(
                    sender_id=sender_id,
                    sender_name=sender_name,
                    message_id=message_id,
                    metadata=metadata,
                    structured_content=structured_content,
                )

                agent_color, agent_icon, crew_member_data = self._metadata_resolver.resolve_agent_metadata(
                    sender_name, metadata
                )

                logger.debug(f"  Agent message with {len(structured_content)} content items, crew_read_by: {len(crew_read_by)}")
                return ChatListItem(
                    message_id=message_id,
                    sender_id=sender_id,
                    sender_name=sender_name,
                    is_user=False,
                    agent_message=agent_message,
                    agent_color=agent_color,
                    agent_icon=agent_icon,
                    crew_member_metadata=crew_member_data,
                    crew_read_by=crew_read_by,
                )

        except Exception as e:
            logger.error(f"Error building item from history: {e}", exc_info=True)
            return None

    def merge_content_into_existing_bubble(self, message_id: str, combined_msg: Dict[str, Any]) -> None:
        """Merge new content into an existing message bubble.

        Processes raw content items from the new batch and merges them into
        the existing model item. Skill content is merged by skill_name,
        and content marked with _skill_name metadata is added as children of
        the matching skill.

        Args:
            message_id: The ID of the message to update
            combined_msg: The combined message data with new content
        """
        try:
            existing_row = self._model.get_row_by_message_id(message_id)
            if existing_row is None:
                return
            current_item = self._model.get_item(existing_row)
            if not current_item:
                return

            current_structured = current_item.get(self._model.STRUCTURED_CONTENT, [])
            # Shallow copy of list only; we replace/filter elements, do not mutate kept items
            merged_content = list(current_structured)
            new_content_list = combined_msg.get("content", [])

            for content_item in new_content_list:
                if not isinstance(content_item, dict):
                    continue

                content_type = content_item.get('content_type', '')
                item_metadata = content_item.get('metadata')
                skill_ref = (item_metadata.get('_skill_name')
                             if isinstance(item_metadata, dict) else None)

                if content_type == 'skill':
                    self._merge_or_append_skill(merged_content, content_item)
                elif skill_ref:
                    self._add_content_to_skill_child(merged_content, content_item, skill_ref)
                elif content_type == 'text':
                    merged_content.append(self._copy_content_item(content_item))
                elif content_type == 'thinking':
                    merged_content = [c for c in merged_content
                                      if c.get('content_type') != 'thinking']
                    merged_content.append(self._copy_content_item(content_item))
                elif content_type == 'typing':
                    merged_content = [c for c in merged_content
                                      if c.get('content_type') != 'typing']
                    merged_content.append(self._copy_content_item(content_item))
                elif content_type == 'crew_member_read':
                    # Extract crew_member_read and update crew_read_by field
                    raw_crew_members = content_item.get("data", {}).get("crew_members", [])
                    crew_read_by = self._resolve_crew_read_by(raw_crew_members)
                    if crew_read_by:
                        # Update the crew_read_by field in the existing item
                        self._model.update_item(message_id, {self._model.CREW_READ_BY: crew_read_by})
                        logger.debug(f"Updated crew_read_by for {message_id[:8]}...: {len(crew_read_by)} members")
                else:
                    content_id = content_item.get('content_id')
                    if content_id:
                        existing_ids = {c.get('content_id') for c in merged_content
                                        if c.get('content_id')}
                        if content_id in existing_ids:
                            continue
                    merged_content.append(self._copy_content_item(content_item))

            updates = {self._model.STRUCTURED_CONTENT: merged_content}
            self._model.update_item(message_id, updates)
            logger.debug(f"Merged {len(new_content_list)} content items into {message_id[:8]}...")

        except Exception as e:
            logger.error(f"Error merging content for {message_id[:8]}...: {e}", exc_info=True)

    def _merge_or_append_skill(
        self, merged_content: List[Dict[str, Any]], new_skill: Dict[str, Any]
    ) -> None:
        """Merge a skill entry with an existing skill in the list, or append it.

        Finds a matching existing skill by skill_name and merges
        state/children. If no match is found, the skill is appended.
        """
        new_data = new_skill.get('data', {})
        new_skill_name = new_data.get('skill_name', '')

        for i, existing in enumerate(merged_content):
            if existing.get('content_type') != 'skill':
                continue
            ed = existing.get('data', {})
            if ed.get('skill_name') == new_skill_name and new_skill_name:
                merged_content[i] = self._merge_skill_dicts(existing, new_skill)
                return

        merged_content.append(self._copy_content_item(new_skill))

    def _add_content_to_skill_child(
        self,
        merged_content: List[Dict[str, Any]],
        child_item: Dict[str, Any],
        skill_name: str,
    ) -> None:
        """Add a content item as a child of the matching skill in the list.

        If no matching skill is found, the item is appended as standalone content.
        """
        for i, existing in enumerate(merged_content):
            if existing.get('content_type') != 'skill':
                continue
            ed = existing.get('data', {})
            if ed.get('skill_name') != skill_name:
                continue

            # Shallow clone of skill dict and data; only child_contents list is extended
            updated = dict(existing)
            updated['data'] = dict(existing.get('data', {}))
            children = list(updated['data'].get('child_contents', []))
            content_id = child_item.get('content_id')
            if content_id:
                existing_ids = {c.get('content_id') for c in children if c.get('content_id')}
                if content_id in existing_ids:
                    return
            children.append(self._copy_content_item(child_item))
            updated['data']['child_contents'] = children
            merged_content[i] = updated
            return

        merged_content.append(self._copy_content_item(child_item))

    def _merge_skill_dicts(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two skill content dicts, using state priority and combining children.

        Args:
            existing: The existing skill dict in the model
            new: The incoming skill dict

        Returns:
            Merged skill dict (deep-copied)
        """
        from agent.chat.content import SkillExecutionState

        existing_data = existing.get('data', {})
        new_data = new.get('data', {})

        existing_state = existing_data.get('state', SkillExecutionState.PENDING.value)
        new_state = new_data.get('state', SkillExecutionState.PENDING.value)

        state_priority = self._get_skill_state_priority()
        existing_prio = state_priority.get(existing_state, 0)
        new_prio = state_priority.get(new_state, 0)

        existing_children = existing_data.get('child_contents', [])
        new_children = new_data.get('child_contents', [])

        merged_children = self.merge_child_contents_by_id(
            existing_children, new_children
        )

        if new_prio >= existing_prio:
            result = dict(new)
            result['data'] = dict(new.get('data', {}))
            result['data']['child_contents'] = merged_children
            if existing.get('content_id'):
                result['content_id'] = existing['content_id']
        else:
            result = dict(existing)
            result['data'] = dict(existing.get('data', {}))
            result['data']['child_contents'] = merged_children
            if new_data.get('progress_text'):
                result['data']['progress_text'] = new_data['progress_text']
            if new_data.get('progress_percentage') is not None:
                result['data']['progress_percentage'] = new_data['progress_percentage']

        return result

    def _get_skill_state_priority(self) -> Dict[str, int]:
        """Get the priority mapping for skill execution states (cached).

        Higher priority states override lower ones during merging.
        """
        if self._skill_state_priority is None:
            from agent.chat.content import SkillExecutionState
            self._skill_state_priority = {
                SkillExecutionState.ERROR.value: 4,
                SkillExecutionState.COMPLETED.value: 3,
                SkillExecutionState.IN_PROGRESS.value: 2,
                SkillExecutionState.PENDING.value: 1,
            }
        return self._skill_state_priority

    def _determine_base_skill_entry(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine which skill entry should be used as the base for merging.

        Single pass: find max-priority entry; if all same priority and in_progress,
        use the last (most recent) entry.
        """
        state_priority = self._get_skill_state_priority()
        in_progress_prio = state_priority.get("in_progress", 2)

        best_entry = entries[0]
        best_prio = state_priority.get(
            best_entry.get("data", {}).get("state", ""), 0
        )
        all_same = True

        for e in entries[1:]:
            prio = state_priority.get(e.get("data", {}).get("state", ""), 0)
            if prio > best_prio:
                best_entry = e
                best_prio = prio
                all_same = False
            elif prio != best_prio:
                all_same = False

        if all_same and best_prio == in_progress_prio:
            return entries[-1]
        return best_entry

    def _merge_child_contents(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge child contents from multiple skill entries.

        Collects all child_contents from entries and removes duplicates
        based on content_id.

        Args:
            entries: List of skill content entries (dict format)

        Returns:
            Merged list of child contents with duplicates removed
        """
        child_contents = []
        seen_content_ids = set()

        for entry in entries:
            entry_children = entry.get("data", {}).get("child_contents", [])
            for child in entry_children:
                content_id = child.get("content_id")
                if content_id:
                    if content_id not in seen_content_ids:
                        child_contents.append(child)
                        seen_content_ids.add(content_id)
                else:
                    # No content_id, just append (can't deduplicate)
                    child_contents.append(child)

        return child_contents

    def _create_skill_content_from_entry(
        self,
        entry: Dict[str, Any],
        skill_name: str,
        child_contents: List[Dict[str, Any]] = None
    ) -> 'StructureContent':
        """Create a SkillContent from an entry dictionary.

        Args:
            entry: The skill entry (dict format)
            skill_name: The name of the skill
            child_contents: Optional child contents to include

        Returns:
            A SkillContent object
        """
        from agent.chat.content import SkillContent, SkillExecutionState, ContentStatus

        base_data = entry.get("data", {})
        final_state = base_data.get("state", SkillExecutionState.IN_PROGRESS.value)

        # Map skill execution state to content status
        if final_state == SkillExecutionState.COMPLETED.value:
            final_status = ContentStatus.COMPLETED
        elif final_state == SkillExecutionState.ERROR.value:
            final_status = ContentStatus.FAILED
        elif final_state == SkillExecutionState.IN_PROGRESS.value:
            final_status = ContentStatus.UPDATING
        else:
            final_status = ContentStatus.CREATING

        return SkillContent(
            content_type=ContentType(entry.get("content_type", "skill")),
            title=entry.get("title", f"Skill: {skill_name}"),
            description=entry.get("description", f"Skill execution: {skill_name}"),
            content_id=entry.get("content_id"),
            status=final_status,
            metadata=entry.get("metadata", {}),
            skill_name=skill_name,
            skill_description=base_data.get("description", ""),
            state=SkillExecutionState(final_state) if isinstance(final_state, str) else final_state,
            progress_text=base_data.get("progress_text", ""),
            progress_percentage=base_data.get("progress_percentage"),
            result=base_data.get("result", ""),
            error_message=base_data.get("error_message", ""),
            child_contents=child_contents if child_contents is not None else [],
        )

    def merge_skill_entries(
        self,
        skill_name: str,
        skill_entries: List[Dict[str, Any]],
        tool_entries: List[Dict[str, Any]] = None,
        extra_child_contents: List[Dict[str, Any]] = None,
    ) -> Optional['StructureContent']:
        """Merge multiple skill entries into a single SkillContent.

        Args:
            skill_name: The name of the skill
            skill_entries: List of skill content dictionaries
            tool_entries: List of tool_call content dictionaries to associate as children
            extra_child_contents: Additional child contents (e.g., thinking/llm_output
                                  marked via _skill_name metadata)

        Returns:
            A merged SkillContent or None if merging fails
        """
        if not skill_entries:
            return None

        tool_entries = tool_entries or []
        extra_child_contents = extra_child_contents or []

        base_entry = self._determine_base_skill_entry(skill_entries)
        child_contents = self._merge_child_contents(skill_entries)

        # Add metadata-marked children (thinking, llm_output, etc.)
        seen_content_ids = {c.get("content_id") for c in child_contents if c.get("content_id")}
        for child in extra_child_contents:
            cid = child.get("content_id")
            if cid and cid in seen_content_ids:
                continue
            child_contents.append(child)
            if cid:
                seen_content_ids.add(cid)

        # Associate unassociated tool_call entries as children only when no
        # explicit metadata-marked children exist (backward compat for older data).
        # With proper marking, inner tool events arrive via extra_child_contents
        # and remaining tool_entries are outer tool events (e.g. execute_skill itself).
        if not extra_child_contents:
            associated_tools: set = set()
            for skill_entry in skill_entries:
                progress_text = skill_entry.get("data", {}).get("progress_text", "")
                if progress_text:
                    for tool_entry in tool_entries:
                        tool_name = tool_entry.get("data", {}).get("tool_name", "")
                        if (tool_name and tool_name in progress_text
                                and tool_entry.get("content_id") not in associated_tools):
                            child_contents.append(tool_entry)
                            associated_tools.add(tool_entry.get("content_id"))

            for tool_entry in tool_entries:
                if tool_entry.get("content_id") not in associated_tools:
                    child_contents.append(tool_entry)

        return self._create_skill_content_from_entry(base_entry, skill_name, child_contents)

    def merge_child_contents_by_id(
        self, base_children: List[Dict[str, Any]], new_children: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge child contents, deduplicating by content_id.

        Args:
            base_children: Base list of children (typically existing/new content)
            new_children: New children to merge in

        Returns:
            Merged list with unique children (deep copied)
        """
        all_children = []
        seen_ids = set()

        # Add base children first (copy so caller's lists are not mutated)
        for child in base_children:
            child_id = child.get("content_id") if isinstance(child, dict) else None
            all_children.append(
                MessageBuilder._copy_content_item(child) if isinstance(child, dict) else copy.deepcopy(child)
            )
            if child_id:
                seen_ids.add(child_id)

        # Add new children not already present
        for child in new_children:
            child_id = child.get("content_id") if isinstance(child, dict) else None
            if child_id and child_id in seen_ids:
                continue
            all_children.append(
                MessageBuilder._copy_content_item(child) if isinstance(child, dict) else copy.deepcopy(child)
            )
            if child_id:
                seen_ids.add(child_id)

        return all_children
