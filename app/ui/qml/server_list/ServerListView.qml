import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

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

                    Button {
                        text: model.enabled ? root.serverLabels.disable : root.serverLabels.enable
                        implicitWidth: 60
                        implicitHeight: 28
                        font.pixelSize: 11
                        font.bold: true
                        flat: true
                        background: Rectangle {
                            radius: 4
                            color: parent.down ? "#3c4042" : (parent.hovered ? (model.enabled ? "#ffa726" : "#66bb6a") : (model.enabled ? "#FF9800" : "#4CAF50"))
                        }
                        contentItem: Label {
                            text: parent.text
                            color: "white"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font: parent.font
                        }
                        onClicked: root.serverBridge.request_toggle(model.name, !model.enabled)
                    }

                    Button {
                        text: root.serverLabels.edit
                        implicitWidth: 50
                        implicitHeight: 28
                        font.pixelSize: 11
                        font.bold: true
                        flat: true
                        background: Rectangle {
                            radius: 4
                            color: parent.down ? "#1565c0" : (parent.hovered ? "#42a5f5" : "#2196F3")
                        }
                        contentItem: Label {
                            text: parent.text
                            color: "white"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font: parent.font
                        }
                        onClicked: root.serverBridge.request_edit(model.name)
                    }

                    Button {
                        text: root.serverLabels.deleteText
                        implicitWidth: 50
                        implicitHeight: 28
                        font.pixelSize: 11
                        font.bold: true
                        enabled: model.canDelete
                        flat: true
                        opacity: model.canDelete ? 1.0 : 0.45
                        background: Rectangle {
                            radius: 4
                            color: !parent.enabled ? "#555555" : (parent.down ? "#b71c1c" : (parent.hovered ? "#ef5350" : "#F44336"))
                        }
                        contentItem: Label {
                            text: parent.text
                            color: parent.enabled ? "white" : "#888888"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font: parent.font
                        }
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
