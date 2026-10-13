// Original maze-chase game for Impasto: smooth tile movement and persistent rounds.
import QtQuick
import Quickshell
import Quickshell.Io
import "../../../theme"
import "../../../services"
import "PacmanLogic.js" as Logic

FocusScope {
    id: root
    property int score: 0
    property bool over: false
    property color tint: Theme.accent
    signal finished(int score)
    property var state: null
    property int revision: 0
    property int wanted: 2
    property bool paused: true
    property bool initialized: false
    property bool snap: true
    property string saveStatus: ""
    readonly property int speed: state ? Math.max(82, 160 - (state.level - 1) * 8) : 160
    readonly property real tile: Math.min((width - 20) / 19, (height - 62) / 19)
    readonly property var pellets: { void root.revision; return root.state ? root.state.pellets : [] }
    readonly property var ghosts: { void root.revision; return root.state ? root.state.ghosts : [] }
    readonly property var player: { void root.revision; return root.state ? Object.assign({}, root.state.player) : ({x:9,y:16,dir:2}) }
    readonly property int level: { void root.revision; return root.state ? root.state.level : 1 }
    readonly property int lives: { void root.revision; return root.state ? root.state.lives : 3 }
    readonly property bool powered: { void root.revision; return root.state && root.state.power > 0 }
    readonly property bool protectedNow: { void root.revision; return root.state && root.state.invulnerable > 0 }
    readonly property var ghostColors: ["#ff6b8a", "#ffafe1", "#55dcff", "#ffb45e"]
    focus: true

    readonly property FileView saveFile: FileView {
        path: `${SettingsService.stateDirectory}/pacman-save.json`
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        onSaved: root.saveStatus = "Saved"
        onSaveFailed: error => {
            root.saveStatus = "Save failed"
            console.warn("Pacman save failed:", error)
        }
    }
    function saveGame(): void {
        if (root.initialized && root.state)
            root.saveFile.setText(JSON.stringify(root.state) + "\n")
    }
    function refresh(): void {
        root.revision++
        root.score = root.state.score
        root.over = root.state.over
    }
    function restart(): void {
        root.snap = true
        root.state = Logic.fresh()
        root.wanted = 2
        root.paused = true
        root.initialized = true
        root.refresh()
        root.saveGame()
        Qt.callLater(() => root.snap = false)
    }
    Component.onCompleted: {
        let saved = null
        try { saved = JSON.parse(root.saveFile.text()) } catch (error) { /* first run */ }
        if (Logic.valid(saved)) {
            root.state = saved
            root.initialized = true
            root.wanted = saved.player.dir
            root.refresh()
            Qt.callLater(() => root.snap = false)
        } else root.restart()
    }
    // Also saves when the island closes or this Loader is destroyed.
    Component.onDestruction: root.saveGame()

    Keys.onPressed: event => {
        let direction = -1
        if (event.key === Qt.Key_Right || event.key === Qt.Key_D) direction = 0
        if (event.key === Qt.Key_Down || event.key === Qt.Key_S) direction = 1
        if (event.key === Qt.Key_Left || event.key === Qt.Key_A) direction = 2
        if (event.key === Qt.Key_Up || event.key === Qt.Key_W) direction = 3
        if (direction >= 0 && !root.over) {
            root.wanted = direction
            root.paused = false
        } else if (event.key === Qt.Key_Space && !root.over) {
            root.paused = !root.paused
            root.saveGame()
        } else if (event.key === Qt.Key_Escape) {
            root.paused = true
            root.saveGame()
            event.accepted = false // Let GamesPanel return to the shelf.
            return
        } else return // R belongs to GamesPanel's Restart action.
        event.accepted = true
    }
    Timer {
        interval: root.speed
        running: root.initialized && !root.paused && !root.over
        repeat: true
        onTriggered: {
            const oldLives = root.state.lives
            const oldLevel = root.state.level
            Logic.step(root.state, root.wanted)
            if (root.state.lives !== oldLives || root.state.level !== oldLevel) {
                root.snap = true
                root.paused = true
                root.wanted = root.state.player.dir
            }
            root.refresh()
            if (root.snap || root.over) root.saveGame()
            if (root.over) root.finished(root.score)
            if (root.snap) Qt.callLater(() => root.snap = false)
        }
    }
    Timer {
        interval: 1000
        running: root.initialized && !root.paused && !root.over
        repeat: true
        onTriggered: root.saveGame()
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: "#080d20"
        border.color: "#253a68"
    }
    Row {
        x: 14; y: 8; spacing: 18
        Text { text: "LEVEL " + root.level; color: "#77cfff"; font.family: Theme.fontMono; font.pixelSize: 12 }
        Text { text: "●".repeat(root.lives); color: "#ffe167"; font.pixelSize: 15 }
        Text { text: root.powered ? "POWER UP" : root.saveStatus; color: root.powered ? "#85fff0" : "#8297bc"; font.pixelSize: 12 }
    }
    Item {
        id: mazeBoard
        width: root.tile * 19; height: root.tile * 19
        anchors.horizontalCenter: parent.horizontalCenter
        y: 32
        Repeater {
            model: 361
            Rectangle {
                required property int index
                readonly property int col: index % 19
                readonly property int row: Math.floor(index / 19)
                visible: Logic.maze[row][col] === "#"
                x: col * root.tile + 2; y: row * root.tile + 2
                width: root.tile - 4; height: root.tile - 4
                radius: 5
                color: "#132550"
                border.color: "#3779de"; border.width: 1
            }
        }
        Repeater {
            model: root.pellets
            Rectangle {
                required property var modelData
                width: modelData.power ? root.tile * 0.42 : 4
                height: width; radius: width / 2
                x: (modelData.x + 0.5) * root.tile - width / 2
                y: (modelData.y + 0.5) * root.tile - height / 2
                color: modelData.power ? "#90fff2" : "#ffe4b6"
                SequentialAnimation on opacity {
                    running: modelData.power; loops: Animation.Infinite
                    NumberAnimation { to: 0.35; duration: 450 }
                    NumberAnimation { to: 1; duration: 450 }
                }
            }
        }
        Repeater {
            model: 4
            Item {
                id: ghost
                required property int index
                readonly property var actor: { void root.revision; return Object.assign({}, root.ghosts[index] ?? ({x:9,y:8,dir:0})) }
                x: actor.x * root.tile; y: actor.y * root.tile
                width: root.tile; height: root.tile
                Behavior on x { enabled: !root.snap; NumberAnimation { duration: root.speed; easing.type: Easing.Linear } }
                Behavior on y { enabled: !root.snap; NumberAnimation { duration: root.speed; easing.type: Easing.Linear } }
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 0.78; height: width
                    radius: width * 0.42
                    color: root.powered ? "#5766e3" : root.ghostColors[ghost.index]
                    Row {
                        anchors.centerIn: parent; spacing: 3
                        Repeater {
                            model: 2
                            Rectangle {
                                width: root.tile * 0.18; height: width * 1.2; radius: width / 2; color: "white"
                                Rectangle {
                                    width: parent.width * 0.5; height: width; radius: width / 2; color: "#17204b"
                                    anchors.centerIn: parent
                                    anchors.horizontalCenterOffset: ghost.actor.dir === 0 ? 1 : ghost.actor.dir === 2 ? -1 : 0
                                    anchors.verticalCenterOffset: ghost.actor.dir === 1 ? 1 : ghost.actor.dir === 3 ? -1 : 0
                                }
                            }
                        }
                    }
                }
            }
        }
        Item {
            id: hero
            x: root.player.x * root.tile; y: root.player.y * root.tile
            width: root.tile; height: root.tile
            opacity: root.protectedNow ? 0.65 : 1
            Behavior on x { enabled: !root.snap; NumberAnimation { duration: root.speed; easing.type: Easing.Linear } }
            Behavior on y { enabled: !root.snap; NumberAnimation { duration: root.speed; easing.type: Easing.Linear } }
            Canvas {
                id: face
                anchors.fill: parent
                property real mouth: 0.18
                rotation: root.player.dir * 90
                onMouthChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    const r = width * 0.42
                    ctx.fillStyle = "#ffe167"
                    ctx.beginPath(); ctx.moveTo(width/2, height/2)
                    ctx.arc(width/2, height/2, r, mouth, Math.PI*2-mouth)
                    ctx.closePath(); ctx.fill()
                }
                SequentialAnimation on mouth {
                    running: !root.paused && !root.over; loops: Animation.Infinite
                    NumberAnimation { to: 0.65; duration: 100 }
                    NumberAnimation { to: 0.08; duration: 100 }
                }
            }
        }
        Rectangle {
            anchors.centerIn: parent
            width: pauseLabel.implicitWidth + 32; height: 64
            radius: 14; color: "#ee080d20"; border.color: "#5075b0"
            visible: root.paused && !root.over
            Text {
                id: pauseLabel
                anchors.centerIn: parent
                text: "READY / PAUSED\nArrow keys to play · Space to pause"
                horizontalAlignment: Text.AlignHCenter
                color: "#e2edff"; font.family: Theme.fontFamily; font.pixelSize: 13
            }
        }
    }
    Text {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 6
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Arrows / WASD  ·  Space pause  ·  Esc save & leave  ·  R new game"
        color: "#8297bc"; font.family: Theme.fontMono; font.pixelSize: 11
    }
}
