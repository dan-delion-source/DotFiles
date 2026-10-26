import QtQuick

// Exact Zenith four-frame sprite and power-profile timings. The original
// assets/code are Unlicensed; provenance is in assets/running-cat/README.md.
// No shell services here: previews/tests can drive this animator directly.
Item {
    id: root
    property string profile: ""
    property bool lively: true
    property bool paused: false
    property real size: 35
    readonly property int frame: ticker.frame
    readonly property int interval: {
        switch (root.profile) {
        case "performance": return 80
        case "turbo": return 50
        case "powersave":
        case "power-saver": return 220
        case "balanced": return 150
        default: return 200
        }
    }
    readonly property bool animating: root.visible && root.lively && !root.paused
    implicitWidth: root.size
    implicitHeight: root.size

    Repeater {
        model: 4
        Image {
            required property int index
            anchors.fill: parent
            source: "../assets/running-cat/cat_f" + index + ".png"
            visible: root.frame === index
            fillMode: Image.PreserveAspectFit
            smooth: true
            cache: true
        }
    }

    Timer {
        id: ticker
        property int frame: 0
        interval: root.interval
        running: root.animating
        repeat: true
        onTriggered: frame = (frame + 1) % 4
    }
}
