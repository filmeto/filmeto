import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../common/buttons" as CommonButtons

// serverRows, serverLabels, serverBridge are set on root from Python after load.

Item {
    id: root
    anchors.fill: parent

    property var serverRows: null
    property var serverLabels: null
    property var serverBridge: null

    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
        border.color: "#3c3c3c"
        border.width: 1
        radius: 4
    }

    ListView {
        id: listView
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: statusBar.top
        anchors.margins: 1
        model: root.serverRows
        clip: true
        spacing: 0
        cacheBuffer: Math.max(height * 2, 400)
        boundsBehavior: Flickable.StopAtBounds

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        delegate: Item {
            id: rowRoot
            width: ListView.view.width
            height: rowLayout.implicitHeight + 16

            Rectangle {
                anchors.fill: parent
                color: rowMa.containsMouse ? "#323232" : "transparent"
            }

            MouseArea {
                id: rowMa
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }

            RowLayout {
                id: rowLayout
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 8
                spacing: 12

                Text {
                    text: "●"
                    font.pixelSize: 14
                    font.bold: true
                    color: model.enabled ? "#4CAF50" : "#F44336"
                    Layout.preferredWidth: 16
                    Layout.alignment: Qt.AlignTop
                    Layout.topMargin: 2
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        text: model.name + " (" + model.serverType + ")"
                        font.bold: true
                        font.pixelSize: 13
                        color: "#E1E1E1"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: model.description ? model.description : root.serverLabels.noDescription
                        font.pixelSize: 10
                        color: "#999999"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: root.serverLabels.pluginPrefix + ": " + model.pluginName
                        font.pixelSize: 9
                        color: "#888888"
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    spacing: 4

                    CommonButtons.WarningButton {
                        text: model.enabled ? root.serverLabels.disable : root.serverLabels.enable
                        size: "small"
                        visible: model.enabled
                        onClicked: root.serverBridge.request_toggle(model.name, !model.enabled)
                    }

                    CommonButtons.SuccessButton {
                        text: model.enabled ? root.serverLabels.disable : root.serverLabels.enable
                        size: "small"
                        visible: !model.enabled
                        onClicked: root.serverBridge.request_toggle(model.name, !model.enabled)
                    }

                    CommonButtons.SecondaryButton {
                        text: root.serverLabels.edit
                        size: "small"
                        onClicked: root.serverBridge.request_edit(model.name)
                    }

                    CommonButtons.DangerButton {
                        text: root.serverLabels.deleteText
                        size: "small"
                        enabled: model.canDelete
                        opacity: model.canDelete ? 1.0 : 0.45
                        onClicked: {
                            if (model.canDelete)
                                root.serverBridge.request_delete(model.name)
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: "#3c3c3c"
            }
        }
    }

    Label {
        anchors.centerIn: listView
        visible: listView.count === 0
        text: root.serverLabels ? root.serverLabels.emptyText : ""
        color: "#666666"
        font.pixelSize: 13
        z: 2
    }

    Rectangle {
        id: statusBar
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 28
        color: "transparent"

        Label {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 8
            text: root.serverLabels ? root.serverLabels.statusLine : ""
            color: "#888888"
            font.pixelSize: 11
        }
    }
}
