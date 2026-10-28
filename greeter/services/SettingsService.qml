pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "../theme"
QtObject {
    id: root
    property bool loaded: false
    property bool failed: false
    property var report: ({})
    readonly property var appearance: report.appearance ?? ({})
    readonly property var settings: appearance.settings ?? ({})
    readonly property bool preview: Quickshell.env("YOZORA_GREETER_PREVIEW") === "1"
    readonly property string user: report.user ?? ""
    readonly property string lockStyle: settings.lockStyle ?? "classic"
    readonly property string lockClock: settings.lockClock ?? "stacked"
    readonly property string clockFormat: settings.clockFormat ?? "HH:mm"
    readonly property bool clockShowsDate: settings.clockShowsDate ?? false
    readonly property bool clockShowsSeconds: settings.clockShowsSeconds ?? false
    readonly property int lockBlur: settings.lockBlur ?? 32
    readonly property real motionScale: settings.motionScale ?? 100
    readonly property string motionCurve: settings.motionCurve ?? "OutCubic"
    readonly property bool islandAttached: false
    readonly property bool notesHandwriting: false
    readonly property string surfaceStyle: "classic"
    readonly property int barHeight: 30
    readonly property int sideBarWidth: 40
    readonly property int barMargin: 8
    readonly property Process reader: Process {
        command: ["python3", Quickshell.shellPath("backend.py"), "read",
                  "--config", Quickshell.env("YOZORA_GREETER_CONFIG") || Quickshell.shellPath("config.json"),
                  "--data", Quickshell.env("YOZORA_GREETER_DATA") || "/var/lib/yozora-greeter"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    root.report = JSON.parse(text)
                    Theme.apply(root.appearance.colors, "Yozora")
                    root.loaded = true
                } catch (error) { root.failed = true }
            }
        }
        onExited: code => { if (code !== 0) root.failed = true }
    }
}
