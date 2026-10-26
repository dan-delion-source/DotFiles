import QtQuick
import QtQuick.Effects
import "../theme"

// This thumbnail only draws. It never constructs a LockService, a password
// field or a Wayland session lock, and it cannot send authentication events.
Item {
    id: root
    property string style: "classic"
    property url wallpaper
    clip: true

    Rectangle { anchors.fill: parent; color: Theme.island }
    Loader {
        anchors.fill: parent
        sourceComponent: root.style === "mainframe" ? terminal : classic
    }
    Component {
        id: terminal
        MainframeView {
            preview: true
            motion: 0
            account: ""
            output: ""
            ink: Theme.text
            accent: Theme.accent
            danger: Theme.red
        }
    }
    Component {
        id: classic
        Item {
            Image {
                id: background
                anchors.fill: parent
                source: root.wallpaper
                sourceSize.width: 480
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: false
            }
            MultiEffect {
                anchors.fill: parent
                source: background
                visible: background.status === Image.Ready
                blurEnabled: true
                blur: 1
                blurMax: 24
            }
            LockClock {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -10
                at: new Date(2026, 0, 1, 9, 41)
                scale: Math.min(root.width / 1100, root.height / 720)
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 14
                width: Math.min(parent.width - 20, 120)
                height: 22
                radius: 11
                color: Theme.island
                Text {
                    anchors.centerIn: parent
                    text: "••••••"
                    font.family: Theme.fontMono
                    font.pixelSize: 10
                    color: Theme.text
                }
            }
        }
    }
}
