// SuccessButton.qml - Positive action button with green color
// Use for positive actions like "Enable", "Activate", "Approve"

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Success button uses success colors
    backgroundColor: Theme.success
    backgroundHoverColor: Theme.successHover
    backgroundPressedColor: Theme.successPressed
    textColor: "white"
}
