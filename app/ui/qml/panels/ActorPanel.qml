import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 8
            spacing: 6

            ToolButton {
                text: "\ue610"
                font.family: "iconfont"
                font.pixelSize: 16
                onClicked: if (actorPanelViewModel) actorPanelViewModel.on_add_clicked()
                ToolTip.visible: hovered
                ToolTip.text: "New Character"
            }

            ToolButton {
                text: "\ue6a7"
                font.family: "iconfont"
                font.pixelSize: 16
                onClicked: if (actorPanelViewModel) actorPanelViewModel.on_draw_clicked()
                ToolTip.visible: hovered
                ToolTip.text: "Random Generate"
            }

            ToolButton {
                text: "\ue653"
                font.family: "iconfont"
                font.pixelSize: 16
                onClicked: if (actorPanelViewModel) actorPanelViewModel.on_extract_clicked()
                ToolTip.visible: hovered
                ToolTip.text: "Extract From Story"
            }

            Item { Layout.fillWidth: true }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "transparent"
            visible: actorModel && actorModel.count === 0

            Text {
                anchors.centerIn: parent
                text: actorPanelViewModel ? actorPanelViewModel.emptyMessage : ""
                color: "#9a9a9a"
                font.pixelSize: 13
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 8
            Layout.rightMargin: 8
            Layout.bottomMargin: 8
            visible: actorModel && actorModel.count > 0

            GridView {
                id: grid
                anchors.fill: parent
                model: actorModel
                cellWidth: 115
                cellHeight: 196
                clip: true

                delegate: Loader {
                    width: 105
                    height: 186
                    source: Qt.resolvedUrl("ActorCard.qml")
                    onLoaded: {
                        item.name = model.name
                        item.description = model.description || ""
                        item.imagePath = model.imagePath || ""
                        item.selected = model.selected
                        item.clicked.connect(function() {
                            if (actorPanelViewModel) actorPanelViewModel.on_actor_clicked(model.name)
                        })
                        item.doubleClicked.connect(function() {
                            if (actorPanelViewModel) actorPanelViewModel.on_actor_double_clicked(model.name)
                        })
                        item.selectionToggled.connect(function(selected) {
                            if (actorPanelViewModel) actorPanelViewModel.on_actor_selection_changed(model.name, selected)
                        })
                    }
                }
            }
        }
    }
}
