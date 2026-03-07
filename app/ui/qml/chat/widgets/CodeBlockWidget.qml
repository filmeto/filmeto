// CodeBlockWidget.qml - Code block with syntax highlighting and copy button
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string code: ""
    property string language: "text"

    readonly property color bgColor: "#1e1e1e"
    readonly property color borderColor: "#404040"
    readonly property color headerColor: "#2d2d2d"
    readonly property color textColor: "#d4d4d4"
    readonly property color accentColor: "#4a90e2"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: column.implicitHeight + 16

    Layout.fillWidth: true

    ColumnLayout {
        id: column
        anchors {
            fill: parent
            margins: 8
        }
        spacing: 0

        // Header with language label and copy button
        RowLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: 8
            spacing: 8

            // Language badge
            Rectangle {
                Layout.preferredWidth: languageLabel.implicitWidth + 12
                Layout.preferredHeight: 24
                color: headerColor
                radius: 4

                Text {
                    id: languageLabel
                    anchors.centerIn: parent
                    text: root.language.toUpperCase()
                    color: textColor
                    font.pixelSize: 11
                    font.family: "monospace"
                    font.weight: Font.Medium
                }
            }

            Item { Layout.fillWidth: true }

            // Copy button
            Button {
                id: copyBtn
                implicitWidth: 32
                implicitHeight: 24

                property bool copyBtnCopied: false

                background: Rectangle {
                    color: copyBtn.hovered ? "#404040" : "transparent"
                    radius: 4
                }

                contentItem: RowLayout {
                    spacing: 4
                    anchors.centerIn: parent

                    Text {
                        text: copyBtn.copyBtnCopied ? "✓" : "📋"
                        font.pixelSize: 12
                    }

                    Text {
                        visible: !copyBtn.copyBtnCopied
                        text: "复制"
                        color: textColor
                        font.pixelSize: 11
                    }
                }

                onClicked: {
                    root.copyToClipboard()
                    copyBtn.copyBtnCopied = true
                    copyResetTimer.restart()
                }

                Timer {
                    id: copyResetTimer
                    interval: 2000
                    onTriggered: copyBtn.copyBtnCopied = false
                }
            }
        }

        // Code content with monospace font and selection support
        Flickable {
            id: codeFlickable
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(codeTextEdit.implicitHeight + 16, 400)

            contentWidth: codeTextEdit.implicitWidth
            contentHeight: codeTextEdit.implicitHeight
            clip: true

            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick

            // TextEdit for selectable code
            TextEdit {
                id: codeTextEdit
                width: Math.max(codeFlickable.width, codeTextEdit.implicitWidth)
                padding: 8
                color: textColor
                font.pixelSize: 13
                font.family: "monospace"
                wrapMode: Text.NoWrap
                textFormat: Text.PlainText
                text: root.code
                readOnly: true
                cursorVisible: false
                selectByMouse: true
                selectionColor: root.accentColor
                selectedTextColor: "#ffffff"

                // Context menu for code
                Menu {
                    id: codeContextMenu

                    MenuItem {
                        text: "复制代码"
                        onTriggered: {
                            codeTextEdit.copy()
                        }
                    }

                    MenuItem {
                        text: "全选"
                        onTriggered: {
                            codeTextEdit.selectAll()
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
                            if (codeTextEdit.selectedText.length > 0) {
                                codeContextMenu.popup()
                            }
                        }
                    }
                }

                // Shortcut for Ctrl+C
                Keys.onPressed: function(event) {
                    if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_C) {
                        if (codeTextEdit.selectedText.length > 0) {
                            codeTextEdit.copy()
                            event.accepted = true
                        }
                    }
                }
            }

            // Scroll event forwarding - pass wheel events to parent when at bounds
            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.NoButton
                propagateComposedEvents: true
                hoverEnabled: true

                onWheel: function(wheel) {
                    var atTop = codeFlickable.contentY <= 0
                    var atBottom = codeFlickable.contentY >= codeFlickable.contentHeight - codeFlickable.height

                    // Scroll direction: positive = down, negative = up
                    var scrollingDown = wheel.angleDelta.y < 0
                    var scrollingUp = wheel.angleDelta.y > 0

                    // Forward to parent when at boundary in scroll direction
                    if ((scrollingDown && atBottom) || (scrollingUp && atTop)) {
                        wheel.accepted = false  // Let event propagate to parent
                    } else {
                        // Manual scroll for smoother experience
                        var delta = -wheel.angleDelta.y / 2
                        var newY = Math.max(0, Math.min(codeFlickable.contentHeight - codeFlickable.height,
                                                         codeFlickable.contentY + delta))
                        codeFlickable.contentY = newY
                        wheel.accepted = true
                    }
                }
            }

            // Custom scrollbar
            ScrollBar.vertical: ScrollBar {
                contentItem: Rectangle {
                    implicitWidth: 8
                    radius: width / 2
                    color: parent.hovered ? "#606060" : "#505050"
                    opacity: parent.active ? 1.0 : 0.5
                }
            }
        }
    }

    // Method to copy code to clipboard
    function copyToClipboard() {
        if (codeTextEdit.selectedText.length > 0) {
            codeTextEdit.copy()
        } else {
            // Copy all code if nothing selected
            codeTextEdit.selectAll()
            codeTextEdit.copy()
            codeTextEdit.deselect()
        }
    }
}
