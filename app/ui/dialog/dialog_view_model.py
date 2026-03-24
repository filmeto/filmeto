"""Canonical ViewModel module for dialog QML chrome."""

from app.ui.dialog.dialog_qml_bridge import (
    CustomDialogTitleBarViewModel,
    DialogTitleDragViewModel,
    MacWindowControlsViewModel,
)

__all__ = [
    "MacWindowControlsViewModel",
    "DialogTitleDragViewModel",
    "CustomDialogTitleBarViewModel",
]
