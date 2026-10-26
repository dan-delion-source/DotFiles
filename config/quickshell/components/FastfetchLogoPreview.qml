import QtQuick
import Quickshell
import Quickshell.Io

import "../theme"

Item {
    id: root

    property string path: ""
    property string kind: "image"
    property string version: ""
    implicitWidth: 118
    implicitHeight: 118
    width: implicitWidth
    height: implicitHeight

    property string art: ""
    readonly property string imageUrl: root.path !== "" && root.kind === "image"
        ? "file://" + root.path.split("/").map(encodeURIComponent).join("/") + "?" + root.version : ""
    readonly property bool animated: /\.(gif|webp)$/i.test(root.path)
    property bool previewFailed: false
    onPathChanged: root.previewFailed = false
    onVersionChanged: {
        root.previewFailed = false
        if (root.kind === "text")
            artFile.reload()
    }

    FileView {
        id: artFile
        path: root.kind === "text" ? root.path : ""
        printErrors: false
        onLoaded: root.art = String(text()).replace(/\u001b\[[0-9;]*m/g, "").replace(/\s+$/, "")
        onLoadFailed: root.previewFailed = true
    }

    Text {
        anchors.centerIn: parent
        visible: root.kind === "text" && !root.previewFailed
        width: 112
        height: 112
        text: root.art
        textFormat: Text.PlainText
        font.family: Theme.fontMono
        font.pixelSize: 9
        fontSizeMode: Text.Fit
        minimumPixelSize: 3
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        lineHeight: 1
        color: Theme.accent
    }

    AnimatedImage {
        anchors.centerIn: parent
        visible: root.kind === "image" && root.animated
        width: 112
        height: 112
        fillMode: Image.PreserveAspectFit
        source: visible ? root.imageUrl : ""
        playing: visible
        cache: false
        onStatusChanged: {
            if (status === Image.Error)
                root.previewFailed = true
        }
    }

    Image {
        anchors.centerIn: parent
        visible: root.kind === "image" && !root.animated
        width: 112
        height: 112
        fillMode: Image.PreserveAspectFit
        source: visible ? root.imageUrl : ""
        cache: false
        onStatusChanged: {
            if (status === Image.Error)
                root.previewFailed = true
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.previewFailed
        text: Tr.t("Preview unavailable")
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fontSizeSmall
        color: Theme.textMuted
    }
}
