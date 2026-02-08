// AudioWidget.qml - Widget for displaying audio content
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
    height: audioColumn.height + 24

    Column {
        id: audioColumn
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            margins: 12
        }
        spacing: 8

        // Audio player
        Row {
            spacing: 12
            width: parent.width

            Button {
                id: playButton
                text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                onClicked: {
                    if (mediaPlayer.playbackState === MediaPlayer.PlayingState) {
                        mediaPlayer.pause()
                    } else {
                        mediaPlayer.play()
                    }
                }
            }

            Slider {
                id: progressSlider
                anchors.verticalCenter: parent.verticalCenter
                from: 0
                to: mediaPlayer.duration
                value: mediaPlayer.position
                onMoved: mediaPlayer.seek(value)
            }

            Text {
                id: timeText
                anchors.verticalCenter: parent.verticalCenter
                text: formatTime(mediaPlayer.position) + " / " + formatTime(mediaPlayer.duration)
                color: "#888888"
                font.pixelSize: 11
            }
        }

        // Caption
        Text {
            id: captionText
            width: parent.width
            text: root.caption
            color: "#888888"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
            visible: root.caption !== ""
        }
    }

    MediaPlayer {
        id: mediaPlayer
        source: root.source
        audioOutput: AudioOutput {}
    }

    function formatTime(milliseconds) {
        if (isNaN(milliseconds) || milliseconds < 0) return "0:00"
        var seconds = Math.floor(milliseconds / 1000)
        var minutes = Math.floor(seconds / 60)
        var secs = seconds % 60
        return minutes + ":" + (secs < 10 ? "0" : "") + secs
    }
}
