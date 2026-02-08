// ChartWidget.qml - Widget for displaying chart data
import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root

    property var chartData: ({})  // Expected: {type: "bar|line|pie", data: {...}, labels: [...]}
    property string title: ""

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: chartColumn.height + 24

    Column {
        id: chartColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        // Title
        Text {
            id: titleText
            width: parent.width
            text: root.title
            color: "#e0e0e0"
            font.pixelSize: 13
            font.weight: Font.Medium
            visible: root.title !== ""
        }

        // Simple bar chart visualization
        Rectangle {
            id: chartArea
            width: parent.width
            height: 150
            color: "#1a1a1a"
            radius: 4
            visible: chartData.type === "bar" && chartData.data

            Row {
                id: barsRow
                anchors {
                    bottom: parent.bottom
                    left: parent.left
                    right: parent.right
                    margins: 8
                }
                height: parent.height - 20
                spacing: 4

                Repeater {
                    model: chartData.data ? Object.keys(chartData.data).length : 0

                    Rectangle {
                        id: bar
                        width: (barsRow.width - (barsRow.spacing * (modelData - 1))) / modelData
                        height: {
                            var keys = Object.keys(chartData.data)
                            var maxValue = Math.max(...Object.values(chartData.data))
                            var value = chartData.data[keys[index]]
                            return (value / maxValue) * (barsRow.height - 20)
                        }
                        color: root.agentColor || "#4a90e2"
                        radius: 2
                        anchors.bottom: parent.bottom

                        Text {
                            anchors {
                                bottom: parent.top
                                horizontalCenter: parent.horizontalCenter
                            }
                            text: {
                                var keys = Object.keys(chartData.data)
                                return chartData.data[keys[index]]
                            }
                            color: "#888888"
                            font.pixelSize: 9
                        }
                    }
                }
            }
        }

        // Data table fallback for other chart types
        Rectangle {
            width: parent.width
            height: dataTable.implicitHeight + 16
            color: "#1a1a1a"
            radius: 4
            visible: chartData.type !== "bar"

            Column {
                id: dataTable
                anchors {
                    top: parent.top
                    left: parent.left
                    right: parent.right
                    margins: 8
                }
                spacing: 4

                Repeater {
                    model: chartData.data ? Object.keys(chartData.data).length : 0

                    Row {
                        spacing: 12
                        width: parent.width

                        Text {
                            text: {
                                var keys = Object.keys(chartData.data)
                                return keys[index]
                            }
                            color: "#888888"
                            font.pixelSize: 11
                            width: parent.width * 0.6
                        }

                        Text {
                            text: {
                                var keys = Object.keys(chartData.data)
                                return chartData.data[keys[index]]
                            }
                            color: "#e0e0e0"
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }
    }
}
