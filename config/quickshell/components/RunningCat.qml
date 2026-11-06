import QtQuick

// Original Zenith four-frame artwork with a quicker running cadence. The original
// assets/code are Unlicensed; provenance is in assets/running-cat/README.md.
// No shell services here: previews/tests can drive this animator directly.
Item {
    id: root
    property string profile: ""
    property bool lively: true
    property bool paused: false
    property real size: 35
    readonly property int frame: sprite.currentFrame
    readonly property int interval: {
        switch (root.profile) {
        case "performance": return 60
        case "turbo": return 50
        case "powersave":
        case "power-saver": return 100
        case "balanced": return 80
        default: return 80
        }
    }
    readonly property bool animating: root.visible && root.lively && !root.paused
    implicitWidth: root.size
    implicitHeight: root.size

    // A single atlas keeps every pose resident. Qt advances the sprite with
    // the scene graph rather than a JS timer that toggles four Image items.
    AnimatedSprite {
        id: sprite
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height * 100 / 56)
        height: width * 56 / 100
        source: "../assets/running-cat/cat_strip.png"
        frameWidth: 100
        frameHeight: 56
        frameCount: 4
        frameDuration: root.interval
        interpolate: false
        smooth: true
        running: true
        paused: !root.animating
    }
}
