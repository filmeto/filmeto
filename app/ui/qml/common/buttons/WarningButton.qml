// WarningButton.qml - Warning action button with orange color
// Use for actions that need attention like "Disable", "Deactivate"

import QtQuick 2.15
import ".."

BaseButton {
    id: root

    // Warning button uses warning colors
    backgroundColor: Theme.warning
    backgroundHoverColor: Theme.warningHover
    backgroundPressedColor: Theme.warningPressed
    textColor: "white"
}
