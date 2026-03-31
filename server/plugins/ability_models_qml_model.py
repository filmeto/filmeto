"""
Qt list model + controller for ability–model configuration rows (QML-facing).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    Property,
    Qt,
    Signal,
    Slot,
)

from server.plugins.ability_model_config import (
    merge_catalog_with_saved,
    normalize_catalog_item,
    serialize_entries,
)


class AbilityModelsConfigModel(QAbstractListModel):
    AbilityRole = Qt.UserRole + 1
    ModelIdRole = Qt.UserRole + 2
    LabelRole = Qt.UserRole + 3
    EnabledRole = Qt.UserRole + 4
    CustomRole = Qt.UserRole + 5
    SectionRole = Qt.UserRole + 6

    filterTextChanged = Signal()
    abilityFilterChanged = Signal()
    sortModeChanged = Signal()
    groupByAbilityChanged = Signal()
    enabledOnlyChanged = Signal()
    customOnlyChanged = Signal()
    persisted = Signal()

    def __init__(
        self,
        parent: Optional[Any] = None,
        on_persist: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self._on_persist = on_persist
        self._entries: List[Dict[str, Any]] = []
        self._display_order: List[int] = []
        self._filter_text = ""
        self._ability_filter = ""
        self._sort_mode = 0
        self._group_by_ability = True
        self._enabled_only = False
        self._custom_only = False

    def roleNames(self):
        return {
            self.AbilityRole: b"ability",
            self.ModelIdRole: b"modelId",
            self.LabelRole: b"label",
            self.EnabledRole: b"enabled",
            self.CustomRole: b"custom",
            self.SectionRole: b"section",
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._display_order)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._display_order):
            return None
        ri = self._display_order[index.row()]
        e = self._entries[ri]
        if role == self.AbilityRole:
            return e["ability"]
        if role == self.ModelIdRole:
            return e["model_id"]
        if role == self.LabelRole:
            return e["label"]
        if role == self.EnabledRole:
            return e["enabled"]
        if role == self.CustomRole:
            return e.get("custom", False)
        if role == self.SectionRole:
            return e["ability"] if self._group_by_ability else ""
        if role == Qt.DisplayRole:
            return e["label"]
        return None

    def _get_filter_text(self) -> str:
        return self._filter_text

    def _set_filter_text(self, value: str) -> None:
        v = value or ""
        if self._filter_text != v:
            self._filter_text = v
            self.filterTextChanged.emit()
            self._refresh_display()

    filterText = Property(str, _get_filter_text, _set_filter_text, notify=filterTextChanged)

    def _get_ability_filter(self) -> str:
        return self._ability_filter

    def _set_ability_filter(self, value: str) -> None:
        v = value or ""
        if self._ability_filter != v:
            self._ability_filter = v
            self.abilityFilterChanged.emit()
            self._refresh_display()

    abilityFilter = Property(str, _get_ability_filter, _set_ability_filter, notify=abilityFilterChanged)

    def _get_sort_mode(self) -> int:
        return self._sort_mode

    def _set_sort_mode(self, value: int) -> None:
        if self._sort_mode != int(value):
            self._sort_mode = int(value)
            self.sortModeChanged.emit()
            self._refresh_display()

    sortMode = Property(int, _get_sort_mode, _set_sort_mode, notify=sortModeChanged)

    def _get_group_by_ability(self) -> bool:
        return self._group_by_ability

    def _set_group_by_ability(self, value: bool) -> None:
        v = bool(value)
        if self._group_by_ability != v:
            self._group_by_ability = v
            self.groupByAbilityChanged.emit()
            self._refresh_display()

    groupByAbility = Property(
        bool, _get_group_by_ability, _set_group_by_ability, notify=groupByAbilityChanged
    )

    def _get_enabled_only(self) -> bool:
        return self._enabled_only

    def _set_enabled_only(self, value: bool) -> None:
        v = bool(value)
        if self._enabled_only != v:
            self._enabled_only = v
            self.enabledOnlyChanged.emit()
            self._refresh_display()

    enabledOnly = Property(bool, _get_enabled_only, _set_enabled_only, notify=enabledOnlyChanged)

    def _get_custom_only(self) -> bool:
        return self._custom_only

    def _set_custom_only(self, value: bool) -> None:
        v = bool(value)
        if self._custom_only != v:
            self._custom_only = v
            self.customOnlyChanged.emit()
            self._refresh_display()

    customOnly = Property(bool, _get_custom_only, _set_custom_only, notify=customOnlyChanged)

    def _passes_filters(self, i: int, include_ability_filter: bool = True) -> bool:
        e = self._entries[i]
        ft = (self._filter_text or "").lower()
        af = (self._ability_filter or "").strip()
        if include_ability_filter and af and af != "__all__" and e["ability"] != af:
            return False
        if self._enabled_only and not bool(e.get("enabled", True)):
            return False
        if self._custom_only and not bool(e.get("custom", False)):
            return False
        if ft:
            blob = f'{e["ability"]} {e["model_id"]} {e["label"]}'.lower()
            if ft not in blob:
                return False
        return True

    def _refresh_display(self) -> None:
        self.beginResetModel()
        self._rebuild_order()
        self.endResetModel()

    def _rebuild_order(self) -> None:
        n = len(self._entries)
        indices = list(range(n))
        self._display_order = [i for i in indices if self._passes_filters(i, include_ability_filter=True)]

        def sort_key(i: int):
            e = self._entries[i]
            if self._sort_mode == 0:
                return (e["ability"], e["model_id"])
            if self._sort_mode == 1:
                return (e["model_id"], e["ability"])
            # Keep list insertion order to support user-driven reordering.
            return (i,)

        self._display_order.sort(key=sort_key)

    @Slot("QVariant", "QVariant")
    def load(self, catalog: Any, saved: Any) -> None:
        norm_cat: List[Dict[str, Any]] = []
        if isinstance(catalog, list):
            for item in catalog:
                if not isinstance(item, dict):
                    continue
                c = normalize_catalog_item(item)
                if c:
                    norm_cat.append(c)
        merged = merge_catalog_with_saved(norm_cat, saved if isinstance(saved, list) else [])
        self.beginResetModel()
        self._entries = merged
        self._sort_mode = 2
        self._rebuild_order()
        self.endResetModel()
        self._emit_persist()

    @Slot(result="QVariant")
    def serialize(self):
        return serialize_entries(self._entries)

    def _emit_persist(self) -> None:
        if self._on_persist:
            self._on_persist()
        self.persisted.emit()

    @Slot(int, bool)
    def setEnabledAt(self, display_row: int, enabled: bool) -> None:
        if display_row < 0 or display_row >= len(self._display_order):
            return
        ri = self._display_order[display_row]
        self._entries[ri]["enabled"] = bool(enabled)
        ix = self.index(display_row, 0)
        self.dataChanged.emit(ix, ix, [self.EnabledRole, self.SectionRole])
        self._emit_persist()

    @Slot(int)
    def removeAt(self, display_row: int) -> None:
        if display_row < 0 or display_row >= len(self._display_order):
            return
        ri = self._display_order[display_row]
        if not self._entries[ri].get("custom"):
            return
        self.beginResetModel()
        del self._entries[ri]
        self._rebuild_order()
        self.endResetModel()
        self._emit_persist()

    @Slot(str, str)
    def addCustomEntry(self, ability: str, model_id: str) -> None:
        ability = (ability or "").strip()
        model_id = (model_id or "").strip()
        if not ability or not model_id:
            return
        self.beginResetModel()
        self._entries.append(
            {
                "ability": ability,
                "model_id": model_id,
                "label": model_id,
                "enabled": True,
                "custom": True,
            }
        )
        self._rebuild_order()
        self.endResetModel()
        self._emit_persist()

    @Slot(result="QVariant")
    def abilityChoices(self):
        seen = []
        for e in self._entries:
            ab = e["ability"]
            if ab not in seen:
                seen.append(ab)
        seen.sort()
        return seen

    @Slot(str, result="QVariant")
    def modelsForAbility(self, ability: str):
        ab = (ability or "").strip()
        out: List[Dict[str, Any]] = []
        for display_row, raw_index in enumerate(self._display_order):
            e = self._entries[raw_index]
            if ab and e["ability"] != ab:
                continue
            out.append(
                {
                    "displayRow": display_row,
                    "ability": e["ability"],
                    "modelId": e["model_id"],
                    "label": e["label"],
                    "enabled": bool(e.get("enabled", True)),
                    "custom": bool(e.get("custom", False)),
                }
            )
        return out

    @Slot(result="QVariant")
    def abilityStats(self):
        stats: Dict[str, Dict[str, int]] = {}
        for i, e in enumerate(self._entries):
            if not self._passes_filters(i, include_ability_filter=False):
                continue
            ab = e["ability"]
            if ab not in stats:
                stats[ab] = {"total": 0, "enabled": 0}
            stats[ab]["total"] += 1
            if bool(e.get("enabled", True)):
                stats[ab]["enabled"] += 1
        result = []
        for ab in sorted(stats.keys()):
            s = stats[ab]
            result.append({"ability": ab, "total": s["total"], "enabled": s["enabled"]})
        return result

    @Slot(int, int)
    def moveAt(self, display_row: int, offset: int) -> None:
        if offset == 0:
            return
        if display_row < 0 or display_row >= len(self._display_order):
            return
        target_display = display_row + int(offset)
        if target_display < 0 or target_display >= len(self._display_order):
            return

        src_raw = self._display_order[display_row]
        dst_raw = self._display_order[target_display]
        src_ability = self._entries[src_raw]["ability"]
        dst_ability = self._entries[dst_raw]["ability"]
        if src_ability != dst_ability:
            return

        # Swap entries and their priorities
        self._entries[src_raw], self._entries[dst_raw] = self._entries[dst_raw], self._entries[src_raw]
        self._refresh_display()
        self._emit_persist()

    @Slot(int)
    def moveToTop(self, display_row: int) -> None:
        """Move entry at display_row to the top of its ability group."""
        if display_row < 0 or display_row >= len(self._display_order):
            return
        if display_row == 0:
            return

        raw_index = self._display_order[display_row]
        ability = self._entries[raw_index]["ability"]

        # Find the first entry with the same ability
        first_same_ability = None
        for i, raw in enumerate(self._display_order):
            if self._entries[raw]["ability"] == ability:
                first_same_ability = i
                break

        if first_same_ability is None or first_same_ability == display_row:
            return

        # Move the entry to the top of its ability group
        src_raw = self._display_order[display_row]
        dst_raw = self._display_order[first_same_ability]

        self._entries[src_raw], self._entries[dst_raw] = self._entries[dst_raw], self._entries[src_raw]
        self._refresh_display()
        self._emit_persist()

    @Slot(int)
    def moveToBottom(self, display_row: int) -> None:
        """Move entry at display_row to the bottom of its ability group."""
        if display_row < 0 or display_row >= len(self._display_order):
            return

        raw_index = self._display_order[display_row]
        ability = self._entries[raw_index]["ability"]

        # Find the last entry with the same ability
        last_same_ability = None
        for i in range(len(self._display_order) - 1, -1, -1):
            raw = self._display_order[i]
            if self._entries[raw]["ability"] == ability:
                last_same_ability = i
                break

        if last_same_ability is None or last_same_ability == display_row:
            return

        # Move the entry to the bottom of its ability group
        src_raw = self._display_order[display_row]
        dst_raw = self._display_order[last_same_ability]

        self._entries[src_raw], self._entries[dst_raw] = self._entries[dst_raw], self._entries[src_raw]
        self._refresh_display()
        self._emit_persist()

    @Slot(int, str, str)
    def updateEntryAt(self, display_row: int, ability: str, model_id: str) -> None:
        if display_row < 0 or display_row >= len(self._display_order):
            return
        ability = (ability or "").strip()
        model_id = (model_id or "").strip()
        if not ability or not model_id:
            return
        raw_index = self._display_order[display_row]
        entry = self._entries[raw_index]
        entry["ability"] = ability
        entry["model_id"] = model_id
        if bool(entry.get("custom", False)):
            entry["label"] = model_id
        self._refresh_display()
        self._emit_persist()
