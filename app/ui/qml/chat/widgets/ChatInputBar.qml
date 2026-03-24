import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    color: "#1f1f1f"
    border.color: "#303030"
    border.width: 1
    radius: 6
    implicitHeight: 120

    property var inputBridge: null

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        TextArea {
            id: inputArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            placeholderText: inputBridge ? inputBridge.placeholder : "Type a message..."
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            color: "#e8e8e8"
            selectionColor: "#4a90e2"
            selectedTextColor: "#ffffff"
            text: inputBridge ? inputBridge.text : ""
            onTextChanged: if (inputBridge) inputBridge.on_text_changed(text)
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Item { Layout.fillWidth: true }
            Button {
                text: inputBridge ? inputBridge.sendLabel : "Send"
                enabled: inputBridge ? inputBridge.enabled : true
                onClicked: if (inputBridge) inputBridge.submit()
            }
        }
    }
}
