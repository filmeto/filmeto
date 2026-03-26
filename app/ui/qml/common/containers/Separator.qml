// Separator.qml - Horizontal or vertical separator line
// Use for dividing content sections

import QtQuick 2.15
import ".."

Rectangle {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Direction
    property string orientation: "horizontal"  // "horizontal" or "vertical"

    // Styling
    property color lineColor: Theme.border
    property int margins: 0

    // ─────────────────────────────────────────────────────────────
    // Size Configuration
    // ─────────────────────────────────────────────────────────────
    width: orientation === "horizontal" ? parent.width - margins * 2 : 1
    height: orientation === "vertical" ? parent.height - margins * 2 : 1
    x: orientation === "horizontal" ? margins : 0
    y: orientation === "vertical" ? margins : 0

    color: lineColor
}
