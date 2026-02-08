// VideoWidget.qml - Widget for displaying video content
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtMultimedia 6.0

Rectangle {
    id: root

    property string source: ""
    property string caption: ""

    color: "#2a2a2a"
    radius: 6
    width: parent.width
    height: videoPlayer.height + (captionText.visible ? captionText.height + 16 : 16)

    Video {
        id: videoPlayer
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 8
        }
        height: 200
        source: root.source

        VideoOutput {
            anchors.fill: parent
        }

        // Playback controls
        Row {
            anchors {
                bottom: parent.bottom
                left: parent.left
                right: parent.right
            }
            spacing: 8
            padding: 8

            Button {
                text: videoPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                onClicked: {
                    if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                        videoPlayer.pause()
                    } else {
                        videoPlayer.play()
                    }
                }
            }

            Slider {
                id: progressSlider
                anchors.verticalCenter: parent.verticalCenter
                from: 0
                to: videoPlayer.duration
                value: videoPlayer.position
                onMoved: videoPlayer.seek(value)
            }
        }
    }

    // Caption
    Text {
        id: captionText
        anchors {
            top: videoPlayer.bottom
            left: parent.left
            right: parent.right
            margins: 8
        }
        text: root.caption
        color: "#888888"
        font.pixelSize: 12
        wrapMode: Text.WordWrap
        visible: root.caption !== ""
    }
}
