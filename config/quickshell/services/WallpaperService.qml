// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   W A L L P A P E R   S E R V I C E                                      │
// │   wallpaper listing and application                                      │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io

// Lists the Pictures wallpaper library and its animated folder, and applies them. Emits
// `applied` instead of calling ThemeService, so the dependency only runs one
// way.
//
// An animated wallpaper is a video mpvpaper plays over a still of it (its
// poster) that awww shows. `currentWallpaper` is always a picture — the
// poster while a video plays — so everything that draws the wallpaper keeps
// drawing one kind of file; `currentMotion` is the video, or empty.
QtObject {
    id: root

    signal applied(string path)

    readonly property string script: Quickshell.shellPath("scripts/theme_manager.py")

    property var wallpapers: []
    // `{ name, path, poster }`, from the `animated` folder beside the stills.
    property var animated: []
    property string currentWallpaper: ""
    property string currentMotion: ""
    readonly property bool scanning: scanProcess.running
    property bool scanPending: false
    property string scanError: ""
    property string error: ""
    property string restoreDetail: ""
    property int libraryVersion: 0
    property string missingChosen: ""
    readonly property string libraryDirectory: Quickshell.env("HOME") + "/Pictures/Wallpapers"
    readonly property bool chosenUnavailable: root.chosen !== "" && root.chosen === root.missingChosen
    onChosenChanged: root.rescan.restart()

    // What was picked: the video while one plays, else the picture. What a
    // profile keeps, and what the picker marks as applied.
    readonly property string chosen: root.currentMotion || root.currentWallpaper

    readonly property var motionExtensions: /\.(mp4|webm|mkv|mov|gif)$/i

    function isMotion(path: string): bool {
        return root.motionExtensions.test(path)
    }

    readonly property Process scanProcess: Process {
        command: [root.script, "list-library", root.chosen]
        running: true
        onStarted: root.scanError = ""
        onExited: exitCode => {
            if (exitCode !== 0)
                root.scanError = "Could not scan wallpapers. Check folder access."
            if (root.scanPending) {
                root.scanPending = false
                root.rescan.restart()
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    console.warn(text.trim())
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const list = root.parseJson(text)
                if (list && Array.isArray(list.wallpapers) && Array.isArray(list.animated)) {
                    root.wallpapers = list.wallpapers
                    root.animated = list.animated
                    root.missingChosen = list.missingChosen ?? ""
                    root.libraryVersion += 1
                }
            }
        }
    }

    readonly property Process libraryWatcher: Process {
        command: ["python3", Quickshell.shellPath("scripts/watch_wallpapers.py"), root.libraryDirectory]
        running: true
        stdout: SplitParser {
            onRead: line => {
                if (line === "changed")
                    root.rescan.restart()
            }
        }
        onExited: root.watchRetry.restart()
    }

    readonly property Timer watchRetry: Timer {
        interval: 3000
        onTriggered: root.libraryWatcher.running = true
    }

    readonly property Timer rescan: Timer {
        interval: 500
        onTriggered: root.scan()
    }

    readonly property Process currentProcess: Process {
        command: [root.script, "get-state"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                const state = root.parseJson(text)
                if (state) {
                    if (state.currentWallpaper)
                        root.currentWallpaper = state.currentWallpaper
                    root.currentMotion = state.currentMotion ?? ""
                }
                if (state && root.asked !== "") {
                    root.asked = ""
                    root.applied(root.currentWallpaper)
                }
            }
        }
    }

    // A video's poster is only known once the script has made it, so the
    // state is read back before anything repaints.
    property string asked: ""

    readonly property Process applyProcess: Process {
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim()) {
                    root.error = text.trim()
                    console.warn(root.error)
                }
            }
        }
        onExited: exitCode => {
            if (exitCode === 0) {
                root.currentProcess.running = true
            } else {
                console.warn("Could not apply wallpaper:", root.asked)
                if (!root.error)
                    root.error = "Could not apply wallpaper. Check awww query; if unavailable, run awww-daemon in a terminal."
                root.asked = ""
            }
        }
    }

    // ── RESTORE AT LOGIN ────────────────────────────────────────────────────
    //
    // awww's own cache stores the resolved path and breaks if the file moves,
    // so restore from the shell's record, which points at the copy in the
    // data directory. The script only paints outputs that show nothing, so a
    // shell restart does not repaint; it exits 3 while the daemon is still
    // starting (quickshell is launched first), hence the retry.
    readonly property Process restoreProcess: Process {
        command: [root.script, "restore"]
        running: true
        onStarted: root.restoreDetail = ""
        stderr: StdioCollector {
            onStreamFinished: root.restoreDetail = text.trim()
        }
        onExited: exitCode => {
            if (exitCode === 3 && restoreRetry.tries < 8) {
                restoreRetry.tries += 1
                restoreRetry.restart()
            } else if (exitCode !== 0) {
                root.error = root.restoreDetail || "Wallpaper restore failed. Check awww query; if unavailable, run awww-daemon in a terminal."
            }
        }
    }

    readonly property Timer restoreRetry: Timer {
        property int tries: 0
        interval: 1500
        onTriggered: root.restoreProcess.running = true
    }

    // ── HOTPLUG ─────────────────────────────────────────────────────────────
    //
    // awww does not paint outputs added after the wallpaper was set. The
    // restore above only touches empty outputs, so rerun it.
    readonly property Connections hotplug: Connections {
        target: Hyprland

        function onRawEvent(event): void {
            if (event.name === "monitoradded" || event.name === "monitoraddedv2")
                root.arriving.restart()
        }
    }

    // One hotplug emits several events, and awww needs a moment to see the
    // new output.
    readonly property Timer arriving: Timer {
        interval: 700
        onTriggered: {
            root.restoreRetry.tries = 0
            root.restoreProcess.running = true
        }
    }

    function parseJson(text: string): var {
        if (!text || text.trim() === "")
            return null
        try {
            return JSON.parse(text)
        } catch (error) {
            console.warn("Cannot parse the wallpaper list:", error)
            return null
        }
    }

    function scan(): void {
        if (root.scanning) {
            root.scanPending = true
            return
        }
        root.scanProcess.running = true
    }

    // ── TRANSITIONS ─────────────────────────────────────────────────────────
    //
    // awww transition types under the shell's labels. `random` picks from
    // these rows rather than using awww's own, which can pick `none`.
    readonly property var transitions: [
        { id: "fade",   label: "Fade",   type: "fade" },
        { id: "wipe",   label: "Wipe",   type: "wipe" },
        { id: "wave",   label: "Wave",   type: "wave" },
        { id: "circle", label: "Circle", type: "center" },
        { id: "outer",  label: "Outer",  type: "outer" },
        { id: "none",   label: "None",   type: "none" },
        { id: "random", label: "Random", type: "" }
    ]

    function transitionType(id: string): string {
        if (id === "random") {
            const pool = root.transitions.filter(entry => entry.type !== "" && entry.type !== "none")
            return pool[Math.floor(Math.random() * pool.length)].type
        }
        const entry = root.transitions.find(entry => entry.id === id)
        return entry && entry.type !== "" ? entry.type : "wipe"
    }

    function apply(path: string): void {
        if (!path || root.applyProcess.running || root.currentProcess.running)
            return
        root.error = ""
        root.asked = path
        root.applyProcess.command = [root.script, "set-wallpaper", path,
                                     root.transitionType(SettingsService.wallpaperTransition)]
        root.applyProcess.running = true
    }
}
