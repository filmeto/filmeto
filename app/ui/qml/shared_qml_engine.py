# -*- coding: utf-8 -*-
"""
Process-wide QQmlEngine for QQuickWidget instances.

Using one engine lets the QML engine reuse its internal component cache for the same
source URLs across widgets, reducing repeated parse/compile work on each window.

For stronger startup wins, ship QML via Qt resources (.qrc) and/or Qt Quick Compiler
(qmltc / qtquickcompiler) in release builds — this module addresses engine-level reuse only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtQml import QQmlEngine

logger = logging.getLogger(__name__)

_engine: Optional[QQmlEngine] = None


def shared_qml_engine() -> QQmlEngine:
    """Singleton QQmlEngine; safe to use from the GUI thread only."""
    global _engine
    if _engine is None:
        _engine = QQmlEngine()
        qml_pkg = Path(__file__).resolve().parent
        ui_dir = qml_pkg.parent
        for p in (qml_pkg, ui_dir):
            if p.is_dir():
                _engine.addImportPath(str(p))
        logger.debug("Shared QQmlEngine created with import paths: %s, %s", qml_pkg, ui_dir)
    return _engine
