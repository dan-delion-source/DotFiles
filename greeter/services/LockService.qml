pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Greetd
import "../theme"
import "../lock/LockStyles.js" as Styles

// Same presentation contract as the session lock; authentication belongs to greetd.
QtObject {
    id: root
    readonly property bool loginMode: true
    readonly property string activeStyle: SettingsService.lockStyle
    readonly property real activeMotion: Styles.motionFactor(Theme.motion)
    // Login replaces the compositor; it cannot reveal an existing desktop as
    // session unlock does. Keep its closing design visible until the final fade.
    readonly property int handoffDuration: Styles.loginExitMs(root.activeStyle, root.activeMotion)
    readonly property int exitDuration: root.handoffDuration
    property string user: SettingsService.user
    property bool awake: true
    property bool authenticating: false
    property bool failed: false
    property bool leaving: false
    property string typed: ""
    property string message: ""
    property bool responseRequired: false
    property bool echoResponse: false
    property string firstResponse: ""
    property bool firstPending: false
    readonly property bool faceReady: false
    readonly property bool faceScanning: false
    readonly property bool faceMatched: false
    signal faceMissed()
    function wake(): void {}
    function rouse(): void { root.awake = true }
    function rest(): void { root.awake = false; root.typed = "" }
    function shotSource(output: string): string { return SettingsService.appearance.wallpaper ?? "" }
    function cancel(): void {
        if (!SettingsService.preview && Greetd.available && Greetd.state !== GreetdState.Inactive
            && Greetd.state !== GreetdState.Launched) Greetd.cancelSession()
        root.firstResponse = ""; root.typed = ""; root.responseRequired = false
        root.firstPending = false
        root.authenticating = false; root.leaving = false; launchDelay.stop()
    }
    function changeUser(name: string): void {
        root.cancel()
        root.user = name.trim()
        root.message = ""; root.failed = false; root.awake = true
    }
    function submit(password: string): void {
        root.typed = ""
        if (SettingsService.preview || !Greetd.available) {
            root.message = "Preview only — authentication is disabled."
            return
        }
        if (root.authenticating || root.leaving || root.user === "") return
        root.failed = false; root.message = ""; root.authenticating = true
        if (root.responseRequired) {
            root.responseRequired = false
            Greetd.respond(password)
        } else {
            root.firstResponse = password
            root.firstPending = true
            Greetd.createSession(root.user)
        }
    }
    readonly property Connections authentication: Connections {
        target: Greetd
        function onAuthMessage(message: string, error: bool, responseRequired: bool, echoResponse: bool): void {
            root.message = message
            root.failed = error
            if (!responseRequired) return
            root.echoResponse = echoResponse
            if (root.firstPending && !echoResponse) {
                const response = root.firstResponse
                root.firstResponse = ""
                root.firstPending = false
                Greetd.respond(response)
            } else {
                root.firstResponse = ""
                root.firstPending = false
                root.responseRequired = true
                root.authenticating = false
            }
        }
        function onAuthFailure(message: string): void {
            root.firstResponse = ""; root.typed = ""; root.responseRequired = false
            root.firstPending = false
            root.authenticating = false; root.failed = true
            root.message = message || "Authentication failed. Try again."
        }
        function onError(error: string): void {
            root.cancel(); root.failed = true; root.message = error
        }
        function onReadyToLaunch(): void {
            root.firstResponse = ""; root.typed = ""; root.authenticating = false
            root.firstPending = false
            root.responseRequired = false; root.leaving = true
            launchDelay.restart()
        }
        function onLaunched(): void { handoff.running = true }
    }
    // Allow the last black frame to present before stopping the compositor.
    // greetd requires the greeter to exit immediately after acknowledgement.
    readonly property Timer launchDelay: Timer {
        interval: root.handoffDuration + 32
        onTriggered: Greetd.launch([Quickshell.shellPath("start-desktop.sh")], [], false)
    }
    readonly property Process handoff: Process {
        command: ["python3", Quickshell.shellPath("handoff.py")]
        onExited: Qt.quit()
    }
}
