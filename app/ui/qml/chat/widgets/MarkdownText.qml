// MarkdownText.qml - Rich markdown text with selection, copy, and link support
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
    property color linkColor: "#5ba0f2"

    implicitWidth: textEdit.implicitWidth
    implicitHeight: textEdit.implicitHeight
    width: parent.width

    TextEdit {
        id: textEdit
        anchors.fill: parent
        color: root.textColor
        font.pixelSize: root.fontPixelSize
        wrapMode: root.wrapMode ? Text.WordWrap : Text.NoWrap
        textFormat: Text.MarkdownText
        selectionColor: root.selectionColor
        selectedTextColor: root.selectedTextColor
        readOnly: true
        text: root.text
        cursorVisible: false
        selectByMouse: true

        onLinkActivated: function(link) {
            Qt.openUrlExternally(link)
        }

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

        Keys.onPressed: function(event) {
            if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                if (textEdit.selectedText.length > 0) {
                    textEdit.copy()
                    event.accepted = true
                }
            }
        }
    }

    function copy() {
        if (textEdit.selectedText.length > 0) {
            textEdit.copy()
        }
    }

    function selectAll() {
        textEdit.selectAll()
    }

    function clearSelection() {
        textEdit.deselect()
    }
}
