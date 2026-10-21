import QtQuick
import Quickshell
import Quickshell.Io

import "../theme"

Item {
    id: root

    property string logo: "arch"
    implicitWidth: 118
    implicitHeight: 118
    width: implicitWidth
    height: implicitHeight

    property string archArt: ""

    FileView {
        path: Quickshell.shellPath("../fastfetch/logos/arch.txt")
        onLoaded: root.archArt = String(text()).replace(/\s+$/, "")
    }

    Text {
        anchors.centerIn: parent
        visible: root.logo === "arch"
        text: root.archArt
        textFormat: Text.PlainText
        font.family: Theme.fontMono
        font.pixelSize: 9
        lineHeight: 1
        color: Theme.accent
    }

    AnimatedImage {
        anchors.centerIn: parent
        visible: root.logo === "cat"
        width: 112
        height: 112
        fillMode: Image.PreserveAspectFit
        source: Qt.resolvedUrl("../../fastfetch/logos/cat.gif")
        playing: visible
        cache: false
    }
}
