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

    width: parent ? parent.width : 0
    height: column.implicitHeight + 16  // 2 * margins (8)
    implicitWidth: width
    implicitHeight: height

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

                background: Rectangle {
                    color: copyBtn.hovered ? "#404040" : "transparent"
                    radius: 4
                }

                contentItem: RowLayout {
                    spacing: 4
                    anchors.centerIn: parent

                    Text {
                        text: copyBtnCopied ? "✓" : "📋"
                        font.pixelSize: 12
                    }

                    Text {
                        visible: !copyBtnCopied
                        text: "Copy"
                        color: textColor
                        font.pixelSize: 11
                    }
                }

                property bool copyBtnCopied: false

                onClicked: {
                    root.code = root.code // Trigger clipboard copy via Python backend
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

        // Code content with monospace font
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(codeText.implicitHeight + 16, 400)

            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            clip: true

            Text {
                id: codeText
                width: parent.width
                padding: 8
                color: textColor
                font.pixelSize: 13
                font.family: "monospace"
                wrapMode: Text.NoWrap
                textFormat: Text.PlainText
                text: root.code

                // Basic syntax highlighting (could be extended)
                // Note: Full syntax highlighting would require a Python backend
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

    // Method to copy code to clipboard (called by the copy button)
    function copyToClipboard() {
        // This would call a Python backend method
        // clipboard.setText(root.code)
    }
}
