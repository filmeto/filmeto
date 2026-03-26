// GhostButton.qml - Minimal button with transparent background
// Use for tertiary actions, tool buttons, or when you want minimal visual weight

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Ghost button has transparent background with subtle hover
    backgroundColor: "transparent"
    backgroundHoverColor: Theme.withAlpha(Theme.textPrimary, 0.08)
    backgroundPressedColor: Theme.withAlpha(Theme.textPrimary, 0.15)
    backgroundDisabledColor: "transparent"
    textColor: Theme.textPrimary
    textDisabledColor: Theme.textDisabled
}
