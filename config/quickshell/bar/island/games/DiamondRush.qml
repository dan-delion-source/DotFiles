// DIAMONDRUSH_FULL_FRONTEND_V1 — original engine, embedded QML display.
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
    property bool connected: false
    property bool paused: false
    property bool helpOpen: false
    property bool menuConfirm: false
    property string framePath: ""
    property string status: "Starting Diamond Rush…"
    property string error: ""
    property int world: -1
    property int stage: -1
    property real lastFrame: Date.now()
    readonly property string statePath: SettingsService.stateDirectory + "/diamondrush-full"
    focus: true

    Process {
        id: bridge
        command: ["python3", Quickshell.shellPath("bar/island/games/diamondrush-full/bridge.py"), "client", "--state", root.statePath]
        stdinEnabled: true
        stdout: SplitParser { onRead: data => root.report(data) }
        stderr: SplitParser { onRead: data => console.warn("Diamond Rush:", data) }
        onExited: (exitCode, exitStatus) => {
            root.connected = false
            if (exitCode !== 0) root.error = "The game connection stopped. Reopen the game to retry."
        }
    }
    function send(command: string): void { if (bridge && bridge.running) bridge.write(command + "\n") }
    function report(line: string): void {
        try {
            const event = JSON.parse(line)
            if (event.type === "frame") {
                framePath = "file://" + encodeURI(event.path)
                connected = true
                lastFrame = Date.now()
                world = event.world
                stage = event.stage
                score = Math.max(0, event.gems)
                if (status === "Starting Diamond Rush…") status = "Ready"
            } else if (event.type === "saved") status = "Game saved"
            else if (event.type === "restored") status = "Saved session restored"
            else if (event.type === "paused") paused = event.paused
            else if (event.type === "error") error = event.message
            else if (event.type === "starting") { error = ""; status = event.message; framePath = "" }
        } catch (failure) { console.warn("Diamond Rush report:", failure) }
    }
    function pauseGame(): void {
        if (!connected) return
        paused = !paused
        send(paused ? "pause" : "resume")
        forceActiveFocus()
    }
    function tapKey(code: int): void {
        if (paused) { paused = false; send("resume") }
        send("tap " + code)
        forceActiveFocus()
    }
    function restart(): void {
        menuConfirm = true
        if (connected) { paused = true; send("pause") }
        forceActiveFocus()
    }
    function keyCode(key: int): int {
        if (key === Qt.Key_Up || key === Qt.Key_W) return 50
        if (key === Qt.Key_Down || key === Qt.Key_S) return 56
        if (key === Qt.Key_Left || key === Qt.Key_A) return 52
        if (key === Qt.Key_Right || key === Qt.Key_D) return 54
        if ([Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Z].indexOf(key) >= 0) return 53
        if (key === Qt.Key_Q) return -6
        if (key === Qt.Key_E || key === Qt.Key_Backspace) return -7
        if (key >= Qt.Key_0 && key <= Qt.Key_9) return 48 + key - Qt.Key_0
        if (key === Qt.Key_Asterisk) return 42
        if (key === Qt.Key_NumberSign) return 35
        return 0
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            if (helpOpen) { helpOpen = false; event.accepted = true; return }
            if (menuConfirm) { menuConfirm = false; event.accepted = true; return }
            send("pause"); paused = true
            event.accepted = false
            return
        }
        if (event.isAutoRepeat) { if (keyCode(event.key)) event.accepted = true; return }
        if (event.key === Qt.Key_P) { pauseGame(); event.accepted = true; return }
        if (event.key === Qt.Key_F1) { helpOpen = !helpOpen; event.accepted = true; return }
        if (helpOpen || menuConfirm) return
        const code = keyCode(event.key)
        if (code) {
            if (paused) { paused = false; send("resume") }
            send("down " + code)
            event.accepted = true
        }
    }
    Keys.onReleased: event => {
        if (event.isAutoRepeat) return
        const code = keyCode(event.key)
        if (code) { send("up " + code); event.accepted = true }
    }
    onActiveFocusChanged: {
        if (!activeFocus && connected && !paused) { paused = true; send("pause") }
    }
    onHelpOpenChanged: {
        if (helpOpen && connected && !paused) { paused = true; send("pause") }
    }
    Component.onCompleted: { bridge.running = true; forceActiveFocus() }
    Component.onDestruction: send("pause")

    Rectangle { anchors.fill: parent; radius: 16; color: "#101e19"; border.color: "#667749"; border.width: 2 }
    Image { x: 18; y: 10; width: 36; height: 36; source: "diamondrush-logo.png"; smooth: false }
    Column {
        x: 64; y: 12; spacing: 3
        Text { text: "DIAMOND RUSH"; color: "#f3d982"; font.family: "monospace"; font.bold: true; font.pixelSize: 18 }
        Text { text: "The complete original campaign"; color: "#9fb194"; font.family: "monospace"; font.pixelSize: 10 }
    }
    Item {
        id: viewport
        x: 16; y: 58; width: parent.width-196; height: parent.height-96
        readonly property real factor: Math.min(width/240,height/320)
        Rectangle { anchors.centerIn: parent; width: 240*viewport.factor+4; height: 320*viewport.factor+4; color: "black"; border.color: "#849360"; border.width: 2 }
        Image {
            id: display
            objectName: "originalGameDisplay"
            anchors.centerIn: parent; width: 240*viewport.factor; height: 320*viewport.factor
            source: root.framePath
            cache: false; asynchronous: false; smooth: false
            fillMode: Image.PreserveAspectFit
        }
        Rectangle {
            anchors.centerIn: parent; width: parent.width-30; height: 105; radius: 8; color: "#ed13261d"; border.color: "#b5a064"
            visible: root.paused || (!root.connected && !root.error)
            Column {
                anchors.centerIn: parent; spacing: 8
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.paused ? "PAUSED" : "DIAMOND RUSH"; color: "#f1da8c"; font.family: "monospace"; font.bold: true; font.pixelSize: 19 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.paused ? "Press P or click to resume" : "Starting the original game…"; color: "#c1cdb0"; font.family: "monospace"; font.pixelSize: 11 }
            }
            MouseArea { anchors.fill: parent; onClicked: { if (root.paused) root.pauseGame() } }
        }
    }
    component Button: Rectangle {
        property string label: ""
        signal clicked()
        width: 148; height: 34; radius: 5
        color: hit.containsMouse ? "#36513a" : "#24392a"; border.color: "#5e7450"
        Text { anchors.centerIn: parent; text: parent.label; color: "#e5e1bd"; font.family: "monospace"; font.pixelSize: 11 }
        MouseArea { id: hit; anchors.fill: parent; hoverEnabled: true; onClicked: parent.clicked() }
    }
    Column {
        x: parent.width-164; y: 64; spacing: 10
        Text { text: "EXPEDITION"; color: "#adb78a"; font.family: "monospace"; font.pixelSize: 12; font.bold: true }
        Button { label: root.paused ? "Resume [P]" : "Pause [P]"; onClicked: root.pauseGame() }
        Button { label: "Save game"; onClicked: { root.send("save"); root.forceActiveFocus() } }
        Button { label: "Original menu"; onClicked: root.restart() }
        Rectangle { width: 148; height: 1; color: "#4d6043" }
        Text { text: "PHONE KEYS"; color: "#adb78a"; font.family: "monospace"; font.pixelSize: 11; font.bold: true }
        Button { label: "Left softkey [Q]"; onClicked: root.tapKey(-6) }
        Button { label: "Right softkey [E]"; onClicked: root.tapKey(-7) }
        Button { label: "Select / act [Space]"; onClicked: root.tapKey(53) }
        Text { text: "Arrows / WASD: move\nSpace / Enter: act\nQ / E: softkeys\nNumbers: phone keypad\nEsc: save and leave"; color: "#afc09e"; font.family: "monospace"; font.pixelSize: 10; lineHeight: 1.5 }
        Button { label: "Controls [F1]"; onClicked: { root.helpOpen = !root.helpOpen; root.forceActiveFocus() } }
    }
    Rectangle {
        anchors.centerIn: parent; width: Math.min(480,parent.width-36); height: 230; radius: 10; color: "#fc13261d"; border.color: "#c3af71"; z: 3
        visible: root.menuConfirm || root.helpOpen || root.error !== ""
        Column {
            anchors.fill: parent; anchors.margins: 20; spacing: 15
            Text { width: parent.width; text: root.error ? "GAME CONNECTION" : root.menuConfirm ? "RETURN TO ORIGINAL MENU?" : "CONTROLS"; color: "#f1da8c"; font.family: "monospace"; font.bold: true; font.pixelSize: 17 }
            Text {
                width: parent.width; wrapMode: Text.WordWrap; color: "#c7d2b1"; font.family: "monospace"; font.pixelSize: 11; lineHeight: 1.35
                text: root.error ? root.error : root.menuConfirm ? "This closes the current instant-resume session and opens the game's original menu. The game's own campaign progress is kept. Choose New Game there if you want a new campaign." : "Use arrows or WASD to move, Space/Enter to select or act, and Q/E for the original left/right softkeys. The game's menus and tutorials explain equipment and special actions. Esc saves and returns to the bar. P pauses."
            }
            Row {
                spacing: 12
                Button { label: root.menuConfirm ? "Open menu" : "Close"; onClicked: {
                    if (root.menuConfirm) { root.send("menu"); root.menuConfirm=false; root.paused=false; root.connected=false; root.status="Opening the original menu…" }
                    else { root.helpOpen=false;root.error="" }
                    root.forceActiveFocus()
                } }
                Button { visible: root.menuConfirm; label: "Cancel"; onClicked: { root.menuConfirm=false; root.forceActiveFocus() } }
            }
        }
    }
    Text {
        x: 18; anchors.bottom: parent.bottom; anchors.bottomMargin: 11; width: parent.width-36; horizontalAlignment: Text.AlignHCenter
        text: root.status; color: "#98ac87"; font.family: "monospace"; font.pixelSize: 10; elide: Text.ElideRight
    }
}
