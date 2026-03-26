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

    def _refresh_display(self) -> None:
        self.beginResetModel()
        self._rebuild_order()
        self.endResetModel()

    def _rebuild_order(self) -> None:
        n = len(self._entries)
        indices = list(range(n))
        ft = (self._filter_text or "").lower()
        af = (self._ability_filter or "").strip()

        def passes(i: int) -> bool:
            e = self._entries[i]
            if af and af != "__all__" and e["ability"] != af:
                return False
            if ft:
                blob = f'{e["ability"]} {e["model_id"]} {e["label"]}'.lower()
                if ft not in blob:
                    return False
            return True

        self._display_order = [i for i in indices if passes(i)]

        def sort_key(i: int):
            e = self._entries[i]
            if self._sort_mode == 0:
                return (e["ability"], e["model_id"])
            return (e["model_id"], e["ability"])

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
