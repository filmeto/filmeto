// SettingsWidget.qml - Application Settings UI
// Tab-based settings interface with search box aligned to the right of tabs

import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    // settingsModel is set on the QML engine context
    property var settingsModel: null

    // Signals
    signal settingsChanged()
    signal closeRequested()

    // Exposed methods
    function save() {
        if (settingsModel && typeof settingsModel.save === 'function') {
            return settingsModel.save()
        }
        return false
    }

    function isDirty() {
        if (settingsModel && typeof settingsModel.isDirty !== 'undefined') {
            return settingsModel.isDirty
        }
        return false
    }

    function cleanup() {
        root.forceActiveFocus()
    }

    // Toast message function
    function showToast(message, isError) {
        toastText.text = message
        toastBar.color = isError ? "#c0392b" : "#27ae60"
        toastBar.opacity = 1
        toastTimer.restart()
    }

    // Background
    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header with TabBar and SearchBox in same row
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 44
            color: "#252525"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 0
                anchors.rightMargin: 16
                spacing: 0

                // Tab Bar (left side)
                TabBar {
                    id: tabBar
                    Layout.fillWidth: true
                    Layout.preferredHeight: parent.height
                    spacing: 2

                    background: Rectangle {
                        color: "#252525"
                    }

                    // Dynamically create tabs from groups
                    Repeater {
                        model: settingsModel ? settingsModel.groups : []

                        TabButton {
                            text: modelData.label || modelData.name
                            width: implicitWidth
                            leftPadding: 20
                            rightPadding: 20

                            background: Rectangle {
                                color: tabBar.currentIndex === index ? "#1e1e1e" : (parent.hovered ? "#2d2d2d" : "#252525")
                                border.color: "#3a3a3a"
                                border.width: 1
                                radius: 4

                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    width: parent.width
                                    height: 1
                                    color: tabBar.currentIndex === index ? "#1e1e1e" : "#3a3a3a"
                                }
                            }

                            contentItem: Text {
                                text: parent.text
                                font.pixelSize: 12
                                color: tabBar.currentIndex === index ? "#ffffff" : "#888888"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }

                    // Services Tab (if available)
                    TabButton {
                        visible: settingsModel ? settingsModel.hasServicesTab : false
                        text: qsTr("Services")
                        width: implicitWidth
                        leftPadding: 20
                        rightPadding: 20

                        background: Rectangle {
                            color: tabBar.currentIndex === servicesTabIndex ? "#1e1e1e" : (parent.hovered ? "#2d2d2d" : "#252525")
                            border.color: "#3a3a3a"
                            border.width: 1
                            radius: 4

                            Rectangle {
                                anchors.bottom: parent.bottom
                                width: parent.width
                                height: 1
                                color: tabBar.currentIndex === servicesTabIndex ? "#1e1e1e" : "#3a3a3a"
                            }
                        }

                        contentItem: Text {
                            text: parent.text
                            font.pixelSize: 12
                            color: tabBar.currentIndex === servicesTabIndex ? "#ffffff" : "#888888"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                // Search Box (right side, aligned with tabs)
                TextField {
                    id: searchField
                    Layout.preferredWidth: 220
                    Layout.preferredHeight: 30
                    Layout.alignment: Qt.AlignVCenter
                    placeholderText: qsTr("Search settings...")
                    selectByMouse: true

                    text: settingsModel ? settingsModel.searchText : ""
                    onTextChanged: {
                        if (settingsModel) {
                            settingsModel.searchText = text
                        }
                    }

                    background: Rectangle {
                        color: "#1e1e1e"
                        border.color: searchField.activeFocus ? "#3498db" : "#3a3a3a"
                        border.width: 1
                        radius: 4
                    }

                    color: "#ffffff"
                    placeholderTextColor: "#606060"
                    leftPadding: 10
                    rightPadding: 30

                    // Search icon
                    Text {
                        anchors.right: parent.right
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: "\u{1F50D}"  // magnifying glass
                        font.pixelSize: 12
                        color: "#606060"
                    }
                }
            }
        }

        // Tab content
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // Dynamically create tab content for each group
            Repeater {
                model: settingsModel ? settingsModel.groups : []

                // Settings Group Tab
                ScrollView {
                    id: groupScrollView
                    clip: true

                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ScrollBar.vertical.policy: ScrollBar.AsNeeded

                    Flickable {
                        id: groupFlickable
                        contentWidth: groupFlickable.width
                        contentHeight: groupContentLayout.implicitHeight + 32

                        ColumnLayout {
                            id: groupContentLayout
                            width: Math.max(groupFlickable.width - 48, 400)
                            x: 24
                            y: 16
                            spacing: 12

                            // Group Header
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Label {
                                    text: modelData.label || modelData.name
                                    font.bold: true
                                    font.pixelSize: 16
                                    color: "#e0e0e0"
                                    Layout.fillWidth: true
                                }

                                Label {
                                    visible: root.searchField.text !== ""
                                    text: qsTr("Showing results for: ") + root.searchField.text
                                    font.pixelSize: 11
                                    color: "#808080"
                                    Layout.fillWidth: true
                                }
                            }

                            // Fields
                            Repeater {
                                model: settingsModel ? settingsModel.get_filtered_fields(modelData.name) : []

                                // Field Item
                                Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: fieldColumn.implicitHeight + 16
                                    color: "#2d2d2d"
                                    radius: 4
                                    border.color: "#3a3a3a"
                                    border.width: 1

                                    property var fieldData: modelData

                                    ColumnLayout {
                                        id: fieldColumn
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 8

                                        // Field Label
                                        Label {
                                            text: fieldData.label + (fieldData.required ? " *" : "")
                                            font.pixelSize: 12
                                            font.bold: true
                                            color: "#ffffff"
                                            Layout.fillWidth: true
                                        }

                                        // Field Widget based on type
                                        Loader {
                                            id: fieldLoader
                                            Layout.fillWidth: true
                                            sourceComponent: {
                                                var type = fieldData.type
                                                if (type === "text" || type === "combo") return textFieldComponent
                                                if (type === "number") return numberFieldComponent
                                                if (type === "boolean") return booleanFieldComponent
                                                if (type === "select") return selectFieldComponent
                                                if (type === "slider") return sliderFieldComponent
                                                if (type === "color") return colorFieldComponent
                                                return textFieldComponent
                                            }

                                            property var fieldItem: fieldData
                                        }

                                        // Field Description
                                        Label {
                                            visible: fieldData.description && fieldData.description !== ""
                                            text: fieldData.description || ""
                                            font.pixelSize: 10
                                            color: "#808080"
                                            wrapMode: Text.WordWrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                }
                            }

                            // Spacer
                            Item {
                                Layout.fillWidth: true
                                Layout.minimumHeight: 20
                                Layout.preferredHeight: 20
                            }
                        }
                    }
                }
            }

            // Services Tab
            Item {
                id: servicesTab
                visible: settingsModel ? settingsModel.hasServicesTab : false

                Label {
                    anchors.centerIn: parent
                    text: qsTr("Services management coming soon...")
                    font.pixelSize: 14
                    color: "#808080"
                }
            }
        }

        // Footer with action buttons
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 50
            color: "#252525"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 20
                anchors.rightMargin: 20
                spacing: 12

                Item { Layout.fillWidth: true }

                // Reset to Default button
                Button {
                    text: qsTr("Reset to Default")
                    implicitHeight: 32

                    background: Rectangle {
                        color: parent.hovered ? "#4a4a4a" : "#3a3a3a"
                        border.color: "#555555"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 12
                        color: "#ffffff"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    onClicked: resetConfirmDialog.open()
                }

                // Revert button
                Button {
                    id: revertBtn
                    text: qsTr("Revert")
                    implicitHeight: 32
                    enabled: settingsModel ? settingsModel.isDirty : false

                    background: Rectangle {
                        color: parent.enabled ? (parent.hovered ? "#4a4a4a" : "#3a3a3a") : "#2a2a2a"
                        border.color: parent.enabled ? "#555555" : "#444444"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 12
                        color: parent.enabled ? "#ffffff" : "#666666"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    onClicked: revertConfirmDialog.open()
                }

                // Save button
                Button {
                    id: saveBtn
                    text: qsTr("Save")
                    implicitHeight: 32
                    enabled: settingsModel ? settingsModel.isDirty : false

                    background: Rectangle {
                        color: parent.enabled ? (parent.hovered ? "#5dade2" : "#3498db") : "#2a2a2a"
                        border.color: parent.enabled ? "#2980b9" : "#444444"
                        border.width: 1
                        radius: 4
                    }

                    contentItem: Text {
                        text: parent.text
                        font.pixelSize: 12
                        font.bold: true
                        color: parent.enabled ? "#ffffff" : "#666666"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    onClicked: {
                        if (settingsModel && settingsModel.save()) {
                            root.settingsChanged()
                        }
                    }
                }
            }
        }
    }

    // Toast notification bar
    Rectangle {
        id: toastBar
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 60
        anchors.horizontalCenter: parent.horizontalCenter
        width: toastText.implicitWidth + 40
        height: 36
        radius: 4
        color: "#27ae60"
        opacity: 0

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }

        Text {
            id: toastText
            anchors.centerIn: parent
            font.pixelSize: 12
            color: "#ffffff"
        }

        Timer {
            id: toastTimer
            interval: 3000
            onTriggered: toastBar.opacity = 0
        }
    }

    // Confirm dialogs
    Dialog {
        id: revertConfirmDialog
        anchors.centerIn: parent
        title: qsTr("Revert Changes")
        modal: true
        standardButtons: Dialog.Yes | Dialog.No

        background: Rectangle {
            color: "#2d2d2d"
            border.color: "#3a3a3a"
            border.width: 1
            radius: 6
        }

        header: Rectangle {
            color: "#252525"
            radius: 6
            implicitHeight: 40

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 6
                color: parent.color
            }

            Text {
                text: revertConfirmDialog.title
                font.bold: true
                font.pixelSize: 14
                color: "#ffffff"
                anchors.centerIn: parent
            }
        }

        contentItem: Text {
            text: qsTr("Are you sure you want to discard all changes?")
            font.pixelSize: 12
            color: "#cccccc"
            wrapMode: Text.WordWrap
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "#252525" }

            Button {
                text: qsTr("No")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                background: Rectangle {
                    color: parent.hovered ? "#4a4a4a" : "#3a3a3a"
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                text: qsTr("Yes")
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle {
                    color: parent.hovered ? "#5dade2" : "#3498db"
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    font.bold: true
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        onAccepted: {
            if (settingsModel) {
                settingsModel.revert()
            }
        }
    }

    Dialog {
        id: resetConfirmDialog
        anchors.centerIn: parent
        title: qsTr("Reset to Default")
        modal: true
        standardButtons: Dialog.Yes | Dialog.No

        background: Rectangle {
            color: "#2d2d2d"
            border.color: "#3a3a3a"
            border.width: 1
            radius: 6
        }

        header: Rectangle {
            color: "#252525"
            radius: 6
            implicitHeight: 40

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 6
                color: parent.color
            }

            Text {
                text: resetConfirmDialog.title
                font.bold: true
                font.pixelSize: 14
                color: "#ffffff"
                anchors.centerIn: parent
            }
        }

        contentItem: Text {
            text: qsTr("Are you sure you want to reset all settings to their default values?")
            font.pixelSize: 12
            color: "#cccccc"
            wrapMode: Text.WordWrap
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "#252525" }

            Button {
                text: qsTr("No")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                background: Rectangle {
                    color: parent.hovered ? "#4a4a4a" : "#3a3a3a"
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }

            Button {
                text: qsTr("Yes")
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle {
                    color: parent.hovered ? "#5dade2" : "#3498db"
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    font.pixelSize: 12
                    font.bold: true
                    color: "#ffffff"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }

        onAccepted: {
            if (settingsModel) {
                settingsModel.reset_to_defaults()
            }
        }
    }

    // Helper property for services tab index
    property int servicesTabIndex: settingsModel && settingsModel.hasServicesTab ?
                                   (settingsModel.groups ? settingsModel.groups.length : 0) : -1

    // Field Components
    Component {
        id: textFieldComponent

        TextField {
            text: settingsModel ? settingsModel.get_value(fieldItem.key) || "" : ""
            selectByMouse: true
            implicitHeight: 32

            background: Rectangle {
                color: "#1e1e1e"
                border.color: parent.activeFocus ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }

            color: "#ffffff"
            placeholderTextColor: "#606060"

            onTextChanged: {
                if (settingsModel) {
                    settingsModel.set_value(fieldItem.key, text)
                }
            }
        }
    }

    Component {
        id: numberFieldComponent

        SpinBox {
            value: settingsModel ? settingsModel.get_value(fieldItem.key) || 0 : 0
            from: fieldItem.validation && fieldItem.validation.min !== undefined ? fieldItem.validation.min : -999999
            to: fieldItem.validation && fieldItem.validation.max !== undefined ? fieldItem.validation.max : 999999
            editable: true
            implicitHeight: 32

            background: Rectangle {
                color: "#1e1e1e"
                border.color: parent.activeFocus ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }

            contentItem: TextInput {
                text: parent.textFromValue(parent.value, parent.locale)
                font.pixelSize: 12
                color: "#ffffff"
                selectionColor: "#3498db"
                selectedTextColor: "#ffffff"
                horizontalAlignment: Qt.AlignHCenter
                verticalAlignment: Qt.AlignVCenter
                readOnly: !parent.editable
                validator: parent.validator
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }

            up.indicator: Rectangle {
                x: parent.mirrored ? 0 : parent.width - width
                height: parent.height
                implicitWidth: 30
                color: parent.up.pressed ? "#3498db" : "#2d2d2d"
                border.color: "#3a3a3a"
                border.width: 1
                radius: 3

                Text {
                    text: "+"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#ffffff"
                    anchors.centerIn: parent
                }
            }

            down.indicator: Rectangle {
                x: parent.mirrored ? parent.width - width : 0
                height: parent.height
                implicitWidth: 30
                color: parent.down.pressed ? "#3498db" : "#2d2d2d"
                border.color: "#3a3a3a"
                border.width: 1
                radius: 3

                Text {
                    text: "-"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#ffffff"
                    anchors.centerIn: parent
                }
            }

            onValueChanged: {
                if (settingsModel) {
                    settingsModel.set_value(fieldItem.key, value)
                }
            }
        }
    }

    Component {
        id: booleanFieldComponent

        RowLayout {
            spacing: 8

            CheckBox {
                id: boolCheckBox
                checked: settingsModel ? settingsModel.get_value(fieldItem.key) || false : false

                indicator: Rectangle {
                    implicitWidth: 18
                    implicitHeight: 18
                    x: boolCheckBox.leftPadding
                    y: parent.height / 2 - height / 2
                    radius: 3
                    border.color: boolCheckBox.checked ? "#3498db" : "#3a3a3a"
                    color: boolCheckBox.checked ? "#3498db" : "#1e1e1e"

                    Text {
                        visible: boolCheckBox.checked
                        text: "\u2713"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#ffffff"
                        anchors.centerIn: parent
                    }
                }

                onCheckedChanged: {
                    if (settingsModel) {
                        settingsModel.set_value(fieldItem.key, checked)
                    }
                }
            }

            Label {
                text: fieldData.description || ""
                font.pixelSize: 10
                color: "#808080"
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
            }
        }
    }

    Component {
        id: selectFieldComponent

        ComboBox {
            id: selectCombo
            implicitHeight: 32
            model: fieldItem.options || []
            textRole: "label"
            valueRole: "value"

            property string currentValue: settingsModel ? settingsModel.get_value(fieldItem.key) || "" : ""

            Component.onCompleted: {
                var idx = indexOfValue(currentValue)
                if (idx >= 0) {
                    currentIndex = idx
                }
            }

            background: Rectangle {
                color: "#1e1e1e"
                border.color: selectCombo.activeFocus ? "#3498db" : "#3a3a3a"
                border.width: 1
                radius: 3
            }

            contentItem: Text {
                text: selectCombo.displayText
                font.pixelSize: 12
                color: "#ffffff"
                verticalAlignment: Text.AlignVCenter
                leftPadding: 10
            }

            delegate: ItemDelegate {
                width: selectCombo.width
                height: 30

                contentItem: Text {
                    text: modelData.label || modelData.value
                    font.pixelSize: 12
                    color: highlighted ? "#ffffff" : "#cccccc"
                    verticalAlignment: Text.AlignVCenter
                }

                background: Rectangle {
                    color: highlighted ? "#3498db" : "#2d2d2d"
                }

                highlighted: selectCombo.highlightedIndex === index
            }

            popup: Popup {
                y: selectCombo.height
                width: selectCombo.width
                implicitHeight: Math.min(contentItem.implicitHeight, 300)
                padding: 1

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: selectCombo.popup.visible ? selectCombo.delegateModel : null
                    currentIndex: selectCombo.highlightedIndex
                }

                background: Rectangle {
                    color: "#2d2d2d"
                    border.color: "#3a3a3a"
                    border.width: 1
                    radius: 3
                }
            }

            onCurrentValueChanged: {
                if (settingsModel && currentValue !== "") {
                    settingsModel.set_value(fieldItem.key, currentValue)
                }
            }
        }
    }

    Component {
        id: sliderFieldComponent

        RowLayout {
            spacing: 12

            Slider {
                id: slider
                Layout.fillWidth: true
                from: fieldItem.validation && fieldItem.validation.min !== undefined ? fieldItem.validation.min : 0
                to: fieldItem.validation && fieldItem.validation.max !== undefined ? fieldItem.validation.max : 100
                stepSize: fieldItem.validation && fieldItem.validation.step !== undefined ? fieldItem.validation.step : 1
                value: settingsModel ? settingsModel.get_value(fieldItem.key) || 0 : 0

                background: Rectangle {
                    x: slider.leftPadding
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    implicitWidth: 200
                    implicitHeight: 4
                    width: slider.availableWidth
                    height: implicitHeight
                    radius: 2
                    color: "#3a3a3a"

                    Rectangle {
                        width: slider.visualPosition * parent.width
                        height: parent.height
                        color: "#3498db"
                        radius: 2
                    }
                }

                handle: Rectangle {
                    x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                    y: slider.topPadding + slider.availableHeight / 2 - height / 2
                    implicitWidth: 16
                    implicitHeight: 16
                    radius: 8
                    color: slider.pressed ? "#5dade2" : "#3498db"
                    border.color: "#2980b9"
                }

                onValueChanged: {
                    if (settingsModel) {
                        settingsModel.set_value(fieldItem.key, Math.round(value))
                    }
                }
            }

            Label {
                text: Math.round(slider.value)
                font.pixelSize: 12
                color: "#ffffff"
                Layout.preferredWidth: 40
            }
        }
    }

    Component {
        id: colorFieldComponent

        RowLayout {
            spacing: 8

            Rectangle {
                width: 32
                height: 32
                radius: 4
                color: settingsModel ? settingsModel.get_value(fieldItem.key) || "#000000" : "#000000"
                border.color: "#3a3a3a"
                border.width: 1
            }

            TextField {
                Layout.fillWidth: true
                text: settingsModel ? settingsModel.get_value(fieldItem.key) || "" : ""
                selectByMouse: true
                implicitHeight: 32

                background: Rectangle {
                    color: "#1e1e1e"
                    border.color: parent.activeFocus ? "#3498db" : "#3a3a3a"
                    border.width: 1
                    radius: 3
                }

                color: "#ffffff"
                placeholderTextColor: "#606060"

                onTextChanged: {
                    if (settingsModel) {
                        settingsModel.set_value(fieldItem.key, text)
                    }
                }
            }
        }
    }

    // Connections to model signals
    Connections {
        target: settingsModel
        function onSettingsChanged() {
            root.settingsChanged()
        }
        function onErrorOccurred(errorMessage) {
            console.log("Settings error:", errorMessage)
        }
    }
}