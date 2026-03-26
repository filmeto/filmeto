// DangerButton.qml - Destructive action button with red color
// Use for destructive actions like "Delete", "Remove", "Discard"

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Danger button uses error colors
    backgroundColor: Theme.error
    backgroundHoverColor: Theme.errorHover
    backgroundPressedColor: Theme.errorPressed
    textColor: "white"
}
