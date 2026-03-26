import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import plugin 1.0

ColumnLayout {
    id: root
    property string filterText: ""
    property bool showFilters: false
    property int sortMode: 2
    property bool enabledOnly: false
    property bool customOnly: false
    property string defaultAbility: "text2image"

    signal filterTextEdited(string text)
    signal toggleFilters()
    signal addClicked(string defaultAbility)
    signal sortModeSelected(int mode)
    signal enabledOnlyToggled(bool checked)
    signal customOnlyToggled(bool checked)

    Layout.fillWidth: true
    spacing: 8

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: filterField
                Layout.fillWidth: true
                implicitHeight: 30
                placeholderText: qsTr("Search ability/model...")
                text: root.filterText
                color: "#e0e0e0"
                placeholderTextColor: "#808080"
                verticalAlignment: TextInput.AlignVCenter
                onTextChanged: root.filterTextEdited(text)
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: filterField.activeFocus ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }

            Button {
                id: filterButton
                text: root.showFilters ? qsTr("Hide Filters") : qsTr("Filters")
                implicitHeight: 30
                onClicked: root.toggleFilters()
                background: Rectangle {
                    color: filterButton.down ? "#252525" : "#1e1e1e"
                    border.color: filterButton.hovered ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: filterButton.text
                    font.pixelSize: 11
                    color: "#e0e0e0"
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        Button {
            id: addButton
            text: qsTr("Add")
            implicitHeight: 30
            onClicked: root.addClicked(root.defaultAbility)
            background: Rectangle {
                color: addButton.down ? "#2980b9" : "#3498db"
                radius: 3
            }
            contentItem: Text {
                text: addButton.text
                color: "#ffffff"
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        visible: root.showFilters
        color: "#2d2d2d"
        border.color: "#3a3a3a"
        radius: 4
        implicitHeight: filterRow.implicitHeight + 14

        RowLayout {
            id: filterRow
            anchors.fill: parent
            anchors.margins: 7
            spacing: 12

            ComboBox {
                id: sortBox
                implicitWidth: 170
                implicitHeight: 28
                model: [qsTr("Sort: ability, model"), qsTr("Sort: model id"), qsTr("Sort: custom order")]
                currentIndex: root.sortMode
                onActivated: index => root.sortModeSelected(index)
                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: sortBox.hovered ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
                contentItem: Text {
                    text: sortBox.displayText
                    color: "#e0e0e0"
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                }
            }

            CheckBox {
                id: enabledOnlyBox
                text: qsTr("Enabled only")
                checked: root.enabledOnly
                onToggled: root.enabledOnlyToggled(checked)
                contentItem: Text {
                    text: enabledOnlyBox.text
                    color: "#b0b0b0"
                    leftPadding: enabledOnlyBox.indicator.width + enabledOnlyBox.spacing
                    verticalAlignment: Text.AlignVCenter
                }
                indicator: Rectangle {
                    implicitWidth: 16
                    implicitHeight: 16
                    x: enabledOnlyBox.leftPadding
                    y: parent.height / 2 - height / 2
                    radius: 3
                    border.color: enabledOnlyBox.checked ? "#3498db" : "#3a3a3a"
                    color: enabledOnlyBox.checked ? "#3498db" : "#1e1e1e"
                }
            }

            CheckBox {
                id: customOnlyBox
                text: qsTr("Custom only")
                checked: root.customOnly
                onToggled: root.customOnlyToggled(checked)
                contentItem: Text {
                    text: customOnlyBox.text
                    color: "#b0b0b0"
                    leftPadding: customOnlyBox.indicator.width + customOnlyBox.spacing
                    verticalAlignment: Text.AlignVCenter
                }
                indicator: Rectangle {
                    implicitWidth: 16
                    implicitHeight: 16
                    x: customOnlyBox.leftPadding
                    y: parent.height / 2 - height / 2
                    radius: 3
                    border.color: customOnlyBox.checked ? "#3498db" : "#3a3a3a"
                    color: customOnlyBox.checked ? "#3498db" : "#1e1e1e"
                }
            }
        }
    }
}