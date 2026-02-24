// SelectableText.qml - Text component with selection and copy functionality
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property string text: ""
    property color textColor: "#e0e0e0"
    property int fontPixelSize: 14
    property real lineHeight: 1.5
    property bool wrapMode: true
    property color selectionColor: "#4a90e2"
    property color selectedTextColor: "#ffffff"

    signal textSelected(string selectedText)

    implicitWidth: textEdit.implicitWidth
    implicitHeight: textEdit.implicitHeight
    width: parent.width

    // TextEdit component for selectable text
    TextEdit {
        id: textEdit
        anchors.fill: parent
        color: root.textColor
        font.pixelSize: root.fontPixelSize
        wrapMode: root.wrapMode ? Text.WordWrap : Text.NoWrap
        textFormat: Text.PlainText
        lineHeight: root.lineHeight
        selectionColor: root.selectionColor
        selectedTextColor: root.selectedTextColor
        readOnly: true
        text: root.text
        cursorVisible: false
        elide: root.wrapMode ? Text.ElideNone : Text.ElideRight

        // Disable text input handling since it's read-only
        onActiveFocusChanged: {
            if (activeFocus) {
                focus = false
            }
        }

        // Emit signal when text is selected
        onSelectedTextChanged: {
            if (selectedText.length > 0) {
                root.textSelected(selectedText)
            }
        }

        // Handle mouse interactions
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            cursorShape: Qt.IBeamCursor
            propagateComposedEvents: true

            property point lastPressedPosition

            onPressed: function(mouse) {
                lastPressedPosition = Qt.point(mouse.x, mouse.y)
                // Let TextEdit handle the press event
                mouse.accepted = false
            }

            onDoubleClicked: function(mouse) {
                textEdit.selectAll()
            }

            onRightClicked: function(mouse) {
                if (textEdit.selectedText.length > 0) {
                    contextMenu.popup()
                }
            }

            // Prevent drag from interfering with selection
            onPositionChanged: function(mouse) {
                if (mouse.pressed && mouse.button === Qt.LeftButton) {
                    mouse.accepted = false
                }
            }
        }
    }

    // Context menu for copy
    Menu {
        id: contextMenu

        MenuItem {
            text: "复制"
            onTriggered: {
                textEdit.copy()
            }
        }

        MenuItem {
            text: "全选"
            onTriggered: {
                textEdit.selectAll()
            }
        }
    }

    // Global shortcut for Ctrl+C
    Shortcut {
        sequence: StandardKey.Copy
        onActivated: {
            if (textEdit.selectedText.length > 0) {
                textEdit.copy()
            }
        }
    }

    // Method to copy selected text
    function copy() {
        if (textEdit.selectedText.length > 0) {
            textEdit.copy()
        }
    }

    // Method to select all text
    function selectAll() {
        textEdit.selectAll()
    }

    // Method to clear selection
    function clearSelection() {
        textEdit.deselect()
    }
}
