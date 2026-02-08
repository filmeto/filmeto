// FileWidget.qml - File attachment display
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property string filePath: ""
    property string fileName: ""
    property int fileSize: 0

    readonly property color bgColor: "#2a2a2a"
    readonly property color bgColorHover: "#353535"
    readonly property color borderColor: "#404040"
    readonly property color textColor: "#d0d0d0"
    readonly property color subtextColor: "#808080"

    color: bgColor
    radius: 8
    border.color: borderColor
    border.width: 1

    width: parent ? parent.width : 0
    height: fileRow.implicitHeight + 20  // 2 * margins (10)
    implicitWidth: width
    implicitHeight: height

    Layout.fillWidth: true

    property bool isHovered: false

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.isHovered = true
        onExited: root.isHovered = false
        onClicked: Qt.openUrlExternally("file://" + root.filePath)
    }

    RowLayout {
        id: fileRow
        anchors {
            fill: parent
            margins: 10
        }
        spacing: 12

        // File icon
        Text {
            text: getFileIcon(root.fileName)
            font.pixelSize: 32

            function getFileIcon(filename) {
                var ext = filename.split('.').pop().toLowerCase()
                switch (ext) {
                    case 'pdf': return '📄'
                    case 'doc':
                    case 'docx': return '📝'
                    case 'xls':
                    case 'xlsx': return '📊'
                    case 'ppt':
                    case 'pptx': return '📈'
                    case 'jpg':
                    case 'jpeg':
                    case 'png':
                    case 'gif': return '🖼️'
                    case 'mp4':
                    case 'mov':
                    case 'avi': return '🎬'
                    case 'mp3':
                    case 'wav': return '🎵'
                    case 'zip':
                    case 'rar':
                    case '7z': return '📦'
                    default: return '📎'
                }
            }
        }

        // File info
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            // File name
            Text {
                Layout.fillWidth: true
                text: root.fileName
                color: textColor
                font.pixelSize: 13
                font.weight: Font.Medium
                elide: Text.ElideMiddle
            }

            // File size
            Text {
                text: formatFileSize(root.fileSize)
                color: subtextColor
                font.pixelSize: 11
            }

            function formatFileSize(bytes) {
                if (bytes < 1024) return bytes + ' B'
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
                if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
                return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
            }
        }

        // Open indicator
        Text {
            text: "→"
            color: textColor
            font.pixelSize: 14
            opacity: isHovered ? 1.0 : 0.5
        }
    }

    Behavior on color {
        ColorAnimation {
            duration: 150
            to: isHovered ? bgColorHover : bgColor
        }
    }
}
