pragma Singleton
import QtQuick
import Quickshell.Io
QtObject {
    id: root
    function run(action: string): void {
        if (SettingsService.preview) return
        if (action !== "shutdown" && action !== "reboot") return
        power.command = ["systemctl", action === "shutdown" ? "poweroff" : "reboot"]
        power.running = true
    }
    readonly property Process power: Process {
        onExited: code => { if (code !== 0) LockService.message = "Power action was not authorized." }
    }
}
