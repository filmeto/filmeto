// CustomDialog.qml - A dialog with proper rounded corners and custom styling
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0
import "../common/buttons" as CommonButtons

Popup {
    id: root

    property string title: ""
    property alias content: contentContainer.sourceComponent
    property int dialogWidth: 420
    property int dialogHeight: -1  // -1 means auto

    signal accepted()
    signal rejected()

    modal: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 0

    width: dialogWidth
    height: dialogHeight > 0 ? dialogHeight : mainColumn.implicitHeight

    anchors.centerIn: parent

    background: Rectangle {
        color: Theme.cardBackground
        radius: 10
        border.color: Theme.border
        border.width: 1
    }

    ColumnLayout {
        id: mainColumn
        anchors.fill: parent
        spacing: 0

        // Title bar
        Rectangle {
            id: titleBar
            Layout.fillWidth: true
            height: 40
            radius: 10
            color: Theme.cardBackground

            // Cover bottom corners
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 10
                color: parent.color
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 8
                spacing: 8

                Label {
                    text: root.title
                    font.bold: true
                    font.pixelSize: 14
                    color: Theme.textPrimary
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Button {
                    implicitWidth: 28
                    implicitHeight: 28
                    onClicked: {
                        root.rejected()
                        root.close()
                    }
                    background: Rectangle {
                        color: parent.hovered ? Qt.lighter(Theme.cardBackground, 1.2) : "transparent"
                        radius: 4
                    }
                    contentItem: Text {
                        text: "\u2715"  // X mark
                        font.pixelSize: 14
                        color: Theme.textSecondary
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        // Separator line
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }

        // Content area
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: contentContainer.implicitHeight
            Layout.leftMargin: 16
            Layout.rightMargin: 16
            Layout.topMargin: 16
            Layout.bottomMargin: 16

            Loader {
                id: contentContainer
                anchors.fill: parent
            }
        }

        // Separator line
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }

        // Button bar
        Rectangle {
            Layout.fillWidth: true
            height: 50
            color: Theme.cardBackground
            radius: 10

            // Cover top corners
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 10
                color: parent.color
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 8

                Item { Layout.fillWidth: true }

                CommonButtons.SecondaryButton {
                    text: qsTr("Cancel")
                    onClicked: {
                        root.rejected()
                        root.close()
                    }
                }

                CommonButtons.PrimaryButton {
                    text: qsTr("OK")
                    onClicked: {
                        root.accepted()
                        root.close()
                    }
                }
            }
        }
    }
}
