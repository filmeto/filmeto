// ChartWidget.qml - Chart data display widget
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var chartData: ({})
    property string chartType: "bar"  // bar, line, pie
    property string title: ""
    property color widgetColor: "#4a90e2"

    implicitWidth: parent.width
    implicitHeight: chartColumn.implicitHeight + 24

    color: "#2a2a2a"
    radius: 6
    border.color: Qt.rgba(widgetColor.r, widgetColor.g, widgetColor.b, 0.3)
    border.width: 1

    Column {
        id: chartColumn
        anchors {
            fill: parent
            margins: 12
        }
        spacing: 12

        // Title
        Text {
            visible: root.title > ""
            width: parent.width
            text: root.title
            color: "#e0e0e0"
            font.pixelSize: 14
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
        }

        // Chart visualization area
        Rectangle {
            width: parent.width
            height: 200
            color: "#1a1a1a"
            radius: 4

            Row {
                anchors {
                    fill: parent
                    margins: 16
                }
                spacing: 0

                // Simple bar chart visualization
                Repeater {
                    model: root.chartData.labels || []

                    Item {
                        width: parent.width / (parent.count > 0 ? parent.count : 1)
                        height: parent.height

                        // Bar
                        Rectangle {
                            id: bar
                            anchors {
                                bottom: parent.bottom
                                horizontalCenter: parent.horizontalCenter
                            }
                            width: parent.width * 0.7
                            height: {
                                var values = root.chartData.values || []
                                var maxValue = Math.max.apply(null, values) || 1
                                return (values[index] / maxValue) * (parent.height - 30)
                            }
                            color: root.widgetColor
                            radius: 2

                            Behavior on height {
                                NumberAnimation {
                                    duration: 500
                                    easing.type: Easing.InOutQuad
                                }
                            }
                        }

                        // Label
                        Text {
                            anchors {
                                bottom: parent.bottom
                                horizontalCenter: parent.horizontalCenter
                            }
                            text: root.chartData.labels[index] || ""
                            color: "#808080"
                            font.pixelSize: 9
                        }

                        // Value tooltip (shown on hover)
                        Rectangle {
                            id: tooltip
                            anchors {
                                bottom: bar.top
                                horizontalCenter: parent.horizontalCenter
                                bottomMargin: 4
                            }
                            width: valueText.implicitWidth + 12
                            height: valueText.implicitHeight + 8
                            color: "#404040"
                            radius: 3
                            visible: mouseArea.containsMouse

                            Text {
                                id: valueText
                                anchors.centerIn: parent
                                text: (root.chartData.values || [])[index] || ""
                                color: "#ffffff"
                                font.pixelSize: 10
                            }
                        }

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                        }
                    }
                }
            }
        }

        // Legend for pie chart or additional info
        Column {
            visible: root.chartType === "pie" && (root.chartData.labels || []).length > 0
            width: parent.width
            spacing: 6

            Repeater {
                model: root.chartData.labels || []

                Row {
                    spacing: 8
                    width: parent.width

                    Rectangle {
                        width: 12
                        height: 12
                        radius: 2
                        color: getChartColor(index, root.chartData.labels.length)
                    }

                    Text {
                        text: root.chartData.labels[index] || ""
                        color: "#d0d0d0"
                        font.pixelSize: 11
                    }

                    Text {
                        text: ": " + (root.chartData.values || [])[index]
                        color: "#808080"
                        font.pixelSize: 11
                    }
                }
            }
        }
    }

    // Generate different colors for pie chart
    function getChartColor(index, total) {
        var colors = [
            root.widgetColor,
            "#ff6b6b",
            "#4ecdc4",
            "#45b7d1",
            "#96ceb4",
            "#ffeaa7",
            "#dfe6e9",
            "#fd79a8"
        ]
        return colors[index % colors.length]
    }
}
