pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "../theme"

// Only public appearance is exported. Installation grants no root access.
QtObject {
    id: root
    property bool installed: false
    property bool pending: false
    property string error: ""
    readonly property string script: Quickshell.shellPath("scripts/greeter.py")
    readonly property Process probe: Process {
        command: ["python3", root.script, "status"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try { root.installed = JSON.parse(text).installed === true }
                catch (error) { root.installed = false }
                root.queue()
            }
        }
    }
    function queue(): void {
        if (root.installed && SettingsService.arrived)
            delay.restart()
    }
    readonly property Timer delay: Timer { interval: 600; onTriggered: root.sync() }
    function sync(): void {
        if (!root.installed || !SettingsService.arrived) return
        if (writer.running) { root.pending = true; return }
        const colors = {}
        for (const key of Theme.tokens) colors[key] = String(Theme[key])
        const settings = {}
        for (const key of ["lockStyle", "lockClock", "clockFormat", "clockShowsDate", "clockShowsSeconds",
                           "lockBlur", "motionScale", "motionCurve"])
            settings[key] = SettingsService[key]
        settings.fontFamily = Theme.fontFamily
        settings.fontMono = Theme.fontMono
        writer.command = ["python3", root.script, "sync", JSON.stringify({
            settings, colors, name: AccountService.name, avatar: AccountService.avatar,
            wallpaper: WallpaperService.currentWallpaper
        })]
        writer.running = true
    }
    readonly property Process writer: Process {
        onStarted: root.error = ""
        stderr: StdioCollector { onStreamFinished: root.error = text.trim() }
        onExited: { if (root.pending) { root.pending = false; root.queue() } }
    }
    readonly property Connections settings: Connections {
        target: SettingsService
        function onArrivedChanged(): void { root.queue() }
        function onLockStyleChanged(): void { root.queue() }
        function onLockClockChanged(): void { root.queue() }
        function onClockFormatChanged(): void { root.queue() }
        function onClockShowsDateChanged(): void { root.queue() }
        function onClockShowsSecondsChanged(): void { root.queue() }
        function onLockBlurChanged(): void { root.queue() }
        function onMotionScaleChanged(): void { root.queue() }
        function onMotionCurveChanged(): void { root.queue() }
    }
    readonly property Connections palette: Connections {
        target: ThemeService
        function onDynamicColorsChanged(): void { root.queue() }
        function onActiveIdChanged(): void { root.queue() }
    }
    readonly property Connections wallpaper: Connections {
        target: WallpaperService
        function onApplied(path: string): void { root.queue() }
    }
    readonly property Connections account: Connections {
        target: AccountService
        function onNameChanged(): void { root.queue() }
        function onAvatarChanged(): void { root.queue() }
        function onRevisionChanged(): void { root.queue() }
    }
}
