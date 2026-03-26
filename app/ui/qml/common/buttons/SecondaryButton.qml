// SecondaryButton.qml - Secondary action button with border
// Use for secondary actions like "Cancel", "Close", "Back"

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Secondary button has border and transparent background
    backgroundColor: "transparent"
    backgroundHoverColor: Theme.withAlpha(Theme.accent, 0.1)
    backgroundPressedColor: Theme.withAlpha(Theme.accent, 0.2)
    textColor: Theme.textPrimary
    textDisabledColor: Theme.textDisabled

    // Override background to add border
    background: Rectangle {
        radius: Theme.radiusMedium
        border.width: 1
        border.color: root.enabled ? (root.hovered ? Theme.borderFocus : Theme.border) : Theme.borderSubtle

        color: {
            if (!root.enabled) return "transparent"
            if (root.down) return root.backgroundPressedColor
            if (root.hovered) return root.backgroundHoverColor
            return root.backgroundColor
        }

        Behavior on color {
            ColorAnimation { duration: Theme.durationFast }
        }

        Behavior on border.color {
            ColorAnimation { duration: Theme.durationFast }
        }
    }
}
