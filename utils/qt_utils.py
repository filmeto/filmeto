from PySide6 import QtWidgets
from PySide6.QtCore import QPoint


def widget_left_x_in_content(w: QtWidgets.QWidget, cw: QtWidgets.QWidget) -> float:
    """Left edge of w in cw's coords; uses global mapping so layout reparenting cannot break the chain."""
    g = w.mapToGlobal(QPoint(0, 0))
    return float(cw.mapFromGlobal(g).x())


def ancestor_widget_with_attr(widget: QtWidgets.QWidget, attr: str):
    """Walk parent widgets until one has the given attribute (e.g. a container API)."""
    w = widget.parentWidget()
    while w is not None:
        if hasattr(w, attr):
            return w
        w = w.parentWidget()
    return None


def remove_last_stretch(layout):
    """移除最后一个 addStretch 添加的 spacer"""
    if layout is not None:
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if isinstance(item, QtWidgets.QSpacerItem):
                layout.removeItem(item)
                break  # 只移除最后一个