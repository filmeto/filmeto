// SelectableText.qml - Text component with selection and copy functionality
import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property string text: ""
    property color textColor: "#e0e0e0"
    property int fontPixelSize: 14
    property bool wrapMode: true
    property color selectionColor: "#4a90e2"
    property color selectedTextColor: "#ffffff"

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
        selectionColor: root.selectionColor
        selectedTextColor: root.selectedTextColor
        readOnly: true
        text: root.text
        cursorVisible: false
        selectByMouse: true

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

        // Handle right-click for context menu
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.RightButton
            cursorShape: Qt.IBeamCursor
            propagateComposedEvents: false

            onClicked: function(mouse) {
                if (mouse.button === Qt.RightButton) {
                    if (textEdit.selectedText.length > 0) {
                        contextMenu.popup()
                    }
                }
            }
        }

        // Handle keyboard shortcut for copy
        Keys.onPressed: function(event) {
            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                if (textEdit.selectedText.length > 0) {
                    textEdit.copy()
                    event.accepted = true
                }
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
