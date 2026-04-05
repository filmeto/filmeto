# -*- coding: utf-8 -*-
"""
Background preflight for edit shell staged load.

Qt widgets must be created on the GUI thread; these callables only perform
cheap import / warm-cache work on a TaskManager worker thread so the main
thread spends less time inside each attach_* step.
"""
import logging

logger = logging.getLogger(__name__)


def preflight_edit_top_bar() -> None:
    """Warm imports for MainWindowTopSideBar and its typical dependencies."""
    try:
        import app.ui.window.edit.top_side_bar  # noqa: F401
        import app.ui.drawing_tools  # noqa: F401
        import app.ui.dialog.mac_button  # noqa: F401
        import app.ui.project_menu.project_menu  # noqa: F401
        import app.ui.server_status  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_top_bar: %s", e)


def preflight_edit_bottom_bar() -> None:
    """Warm imports for MainWindowBottomSideBar / PlayControlWidget."""
    try:
        import app.ui.play_control  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_bottom_bar: %s", e)


def preflight_edit_h_layout() -> None:
    """Warm imports for MainWindowHLayout and side bars."""
    try:
        import app.ui.window.edit.h_layout  # noqa: F401
        import app.ui.window.edit.left_side_bar  # noqa: F401
        import app.ui.window.edit.right_side_bar  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_h_layout: %s", e)


def preflight_edit_center_workspace() -> None:
    """Warm imports for MainWindowWorkspace subtree."""
    try:
        import app.ui.window.edit.workspace  # noqa: F401
        import app.ui.window.edit.workspace_top  # noqa: F401
        import app.ui.window.edit.workspace_bottom  # noqa: F401
    except Exception as e:
        logger.debug("preflight_edit_center_workspace: %s", e)


PREFLIGHT_BY_STAGE = (
    preflight_edit_top_bar,
    preflight_edit_bottom_bar,
    preflight_edit_h_layout,
    preflight_edit_center_workspace,
)
