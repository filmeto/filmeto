// Card.qml - Styled card container with border and background
// Use for grouping related content

import QtQuick 2.15
import ".."

Rectangle {
    id: root

    // ─────────────────────────────────────────────────────────────
    // Public API
    // ─────────────────────────────────────────────────────────────

    // Content
    default property alias content: contentItem.data

    // Styling
    property bool bordered: true
    property bool elevated: false
    property int padding: Theme.spacingMedium

    // ─────────────────────────────────────────────────────────────
    // Rectangle Configuration
    // ─────────────────────────────────────────────────────────────
    color: Theme.cardBackground
    radius: Theme.radiusMedium
    border.color: bordered ? Theme.border : "transparent"
    border.width: bordered ? 1 : 0

    // ─────────────────────────────────────────────────────────────
    // Shadow for elevated cards
    // ─────────────────────────────────────────────────────────────
    Rectangle {
        visible: root.elevated
        anchors.fill: parent
        anchors.margins: -2
        z: -1
        radius: root.radius + 2
        color: Theme.withAlpha("#000000", 0.15)
    }

    // ─────────────────────────────────────────────────────────────
    // Content Container
    // ─────────────────────────────────────────────────────────────
    Item {
        id: contentItem
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
