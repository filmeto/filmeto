// TableWidget.qml - Display tables
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var tableData: ({})  // Expected: {headers: [], rows: [[], ...]}

    readonly property color bgColor: "#2a2a2a"
    readonly property color headerColor: "#353535"
    readonly property color borderColor: "#404040"
    readonly property color textColor: "#d0d0d0"
    readonly property color alternateColor: "#303030"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    implicitWidth: parent.width
    implicitHeight: tableColumn.implicitHeight + 16

    Layout.fillWidth: true

    ScrollView {
        anchors {
            fill: parent
            margins: 8
        }

        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        clip: true

        ColumnLayout {
            id: tableColumn
            width: parent.width
            spacing: 0

            // Header row
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: headerRow.implicitHeight + 12
                color: headerColor
                radius: 6

                Row {
                    id: headerRow
                    anchors {
                        left: parent.left
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                        margins: 6
                    }
                    spacing: 8

                    Repeater {
                        model: root.tableData.headers || []

                        delegate: Text {
                            text: modelData
                            color: textColor
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            width: (parent.width - (root.tableData.headers.length - 1) * 8) / root.tableData.headers.length
                        }
                    }
                }
            }

            // Data rows
            Repeater {
                model: root.tableData.rows || []

                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: dataRow.implicitHeight + 10
                    color: index % 2 === 0 ? "transparent" : alternateColor

                    Row {
                        id: dataRow
                        anchors {
                            left: parent.left
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                            margins: 5
                        }
                        spacing: 8

                        Repeater {
                            model: modelData.length

                            delegate: Text {
                                text: modelData[index]
                                color: textColor
                                font.pixelSize: 12
                                width: (parent.width - (modelData.length - 1) * 8) / modelData.length
                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
            contentItem: Rectangle {
                implicitWidth: 8
                radius: width / 2
                color: parent.hovered ? "#606060" : "#505050"
                opacity: parent.active ? 1.0 : 0.5
            }
        }
    }
}
