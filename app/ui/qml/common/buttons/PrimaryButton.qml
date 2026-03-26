// PrimaryButton.qml - Main action button with accent color
// Use for primary actions like "Save", "Submit", "Confirm"

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Primary button uses accent colors by default
    backgroundColor: Theme.accent
    backgroundHoverColor: Theme.accentHover
    backgroundPressedColor: Theme.accentPressed
    textColor: "white"
}
