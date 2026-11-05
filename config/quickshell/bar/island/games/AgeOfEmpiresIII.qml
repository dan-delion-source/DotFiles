// Age of Empires III original J2ME engine frontend for QuickShell.
// Retro frame with keyboard-only controls; native game image remains 1:1.
import QtQuick
import Quickshell
import Quickshell.Io
import "../../../theme"
import "../../../services"

FocusScope {
    id: root
    property int score: 0
    property bool over: false
    property color tint: Theme.accent
    signal finished(int score)

    property string framePath: ""
    property bool showFirst: true
    property int pendingBuffer: -1

    function enqueueFrame(path) {
        const url = "file://" + encodeURI(path)
        const next = showFirst ? 1 : 0
        pendingBuffer = next
        if (next === 0) {
            firstImage.source = url
            if (firstImage.status === Image.Ready) { showFirst = true; pendingBuffer = -1 }
        } else {
            secondImage.source = url
            if (secondImage.status === Image.Ready) { showFirst = false; pendingBuffer = -1 }
        }
    }
    property string error: ""
    property bool connected: false
    focus: true

    Process {
        id: runner
        command: ["python3", Quickshell.shellPath("bar/island/games/aoe3/bridge.py")]
        stdinEnabled: true
        stdout: SplitParser {
            onRead: line => {
                try {
                    const event = JSON.parse(line)
                    if (event.type === "frame") {
                        root.enqueueFrame(event.path)
                        root.connected = true
                    } else if (event.type === "error") {
                        root.error = event.message
                    }
                } catch (e) {
                    console.warn("Age of Empires III", e)
                }
            }
        }
        stderr: SplitParser {
            onRead: line => console.warn("Age of Empires III", line)
        }
        onExited: (code, status) => {
            if (code !== 0 && !root.error)
                root.error = "Runtime exited; check the Age of Empires III log"
        }
    }

    function send(s) {
        if (runner.running) runner.write(s + "\n")
    }
    function phoneCode(k) {
        if (k === Qt.Key_Left || k === Qt.Key_A) return 52
        if (k === Qt.Key_Right || k === Qt.Key_D) return 54
        if (k === Qt.Key_Up || k === Qt.Key_W) return 50
        if (k === Qt.Key_Down || k === Qt.Key_S) return 56
        if (k === Qt.Key_Space || k === Qt.Key_Return || k === Qt.Key_Enter || k === Qt.Key_Z) return 53
        if (k === Qt.Key_Q) return -6
        if (k === Qt.Key_E || k === Qt.Key_Backspace) return -7
        if (k >= Qt.Key_0 && k <= Qt.Key_9) return 48 + k - Qt.Key_0
        return 0
    }
    Keys.onPressed: event => {
        if (event.isAutoRepeat) return
        const k = phoneCode(event.key)
        if (k) { send("down " + k); event.accepted = true }
    }
    Keys.onReleased: event => {
        if (event.isAutoRepeat) return
        const k = phoneCode(event.key)
        if (k) { send("up " + k); event.accepted = true }
    }
    Component.onCompleted: {
        runner.running = true
        forceActiveFocus()
    }
    Component.onDestruction: send("detach")

    // The outer panel uses the Diamond Rush 640x680 ratio; the 128x128 game stays
    // square and centered. We never stretch it to fill the portrait panel.
    Rectangle {
        anchors.fill: parent
        color: "#122636"
        radius: 14
        border.width: 2
        border.color: "#538ab0"
    }
    Rectangle {
        anchors.fill: parent
        anchors.margins: 7
        color: "transparent"
        radius: 10
        border.width: 1
        border.color: "#3d6479"
    }
    Text {
        anchors.top: parent.top
        anchors.topMargin: 18
        anchors.horizontalCenter: parent.horizontalCenter
        text: "AGE OF EMPIRES III"
        color: "#f5e8b7"
        font.bold: true
        font.pixelSize: 16
    }
    Rectangle {
        id: inset
        anchors.centerIn: parent
        // 12px interior margin gives room for the visible double border.
        readonly property real scaleFactor: Math.min((root.width - 32) / 128, (root.height - 106) / 128)
        readonly property real pixelScale: scaleFactor >= 1 ? Math.floor(scaleFactor) : Math.max(0.1, scaleFactor)
        width: 128 * pixelScale + 8
        height: 128 * pixelScale + 8
        color: "#060c10"
        border.width: 2
        border.color: "#80b9d4"

        Item {
            anchors.centerIn: parent
            width: 128 * inset.pixelScale
            height: 128 * inset.pixelScale
            clip: true
            Image {
                id: firstImage
                anchors.fill: parent
                source: ""
                visible: root.showFirst && status === Image.Ready
                cache: false
                asynchronous: false
                smooth: false
                fillMode: Image.PreserveAspectFit
                onStatusChanged: {
                    if (status === Image.Ready && root.pendingBuffer === 0) {
                        root.showFirst = true
                        root.pendingBuffer = -1
                    }
                }
            }
            Image {
                id: secondImage
                anchors.fill: parent
                source: ""
                visible: !root.showFirst && status === Image.Ready
                cache: false
                asynchronous: false
                smooth: false
                fillMode: Image.PreserveAspectFit
                onStatusChanged: {
                    if (status === Image.Ready && root.pendingBuffer === 1) {
                        root.showFirst = false
                        root.pendingBuffer = -1
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: !root.connected || !!root.error
                text: root.error || "Starting original game…"
                color: "white"
                font.pixelSize: 11
                wrapMode: Text.Wrap
                width: parent.width - 8
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}
