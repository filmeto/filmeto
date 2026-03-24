import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    required property string name
    required property string description
    required property string imagePath
    required property bool selected
    signal clicked()
    signal doubleClicked()
    signal selectionToggled(bool selected)

    width: 105
    height: 186
    radius: 8
    color: hoveredArea.containsMouse ? "#3a3a3a" : "#2d2d2d"
    border.width: 2
    border.color: selected ? "#3498db" : "#3a3a3a"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            ToolButton {
                text: root.selected ? "\ue675" : "\ue673"
                font.family: "iconfont"
                font.pixelSize: 13
                onClicked: root.selectionToggled(!root.selected)
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 6
            color: "#252525"
            border.color: "#333333"
            clip: true

            Image {
                anchors.fill: parent
                source: root.imagePath ? "file://" + root.imagePath : ""
                fillMode: Image.PreserveAspectFit
                visible: root.imagePath !== ""
            }

            Text {
                anchors.centerIn: parent
                visible: root.imagePath === ""
                text: "\ue60c"
                font.family: "iconfont"
                font.pixelSize: 40
                color: "#3498db"
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.name
            color: "#ffffff"
            font.pixelSize: 10
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: hoveredArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        onClicked: root.clicked()
        onDoubleClicked: root.doubleClicked()
    }
}
