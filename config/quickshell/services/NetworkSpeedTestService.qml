pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

// An internet throughput estimate, started only by Network Manager's Test
// button. The singleton keeps the result when its panel is closed and opened.
Singleton {
    id: root

    property string phase: "idle"
    property string message: ""
    property string connection: ""
    property real downloadMbps: -1
    property real uploadMbps: -1

    readonly property bool testing: root.phase === "download" || root.phase === "upload"
    readonly property string script: Quickshell.shellPath("scripts/network_speed_test.py")

    function start(connectionName: string): void {
        if (root.testing || runner.running)
            return
        root.connection = connectionName
        root.downloadMbps = -1
        root.uploadMbps = -1
        root.message = ""
        root.phase = "download"
        runner.command = ["python3", root.script]
        runner.running = true
        watchdog.restart()
    }

    function cancel(): void {
        if (!root.testing)
            return
        root.phase = "idle"
        root.message = "Test cancelled"
        root.downloadMbps = -1
        root.uploadMbps = -1
        watchdog.stop()
        runner.running = false
    }

    function ingest(line: string): void {
        let event
        try {
            event = JSON.parse(line)
        } catch (error) {
            return
        }
        if (!root.testing)
            return
        if (event.event === "phase") {
            root.phase = event.name === "upload" ? "upload" : "download"
        } else if (event.event === "partial" && event.name === "download") {
            root.downloadMbps = event.mbps
        } else if (event.event === "result") {
            root.downloadMbps = event.download_mbps
            root.uploadMbps = event.upload_mbps
            root.phase = "done"
            watchdog.stop()
        } else if (event.event === "error") {
            root.message = event.message
            root.phase = "error"
            watchdog.stop()
        }
    }

    readonly property Process runner: Process {
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: line => root.ingest(line)
        }
        onExited: {
            Qt.callLater(() => {
                if (root.testing && !runner.running) {
                    root.phase = "error"
                    root.message = "The speed test stopped unexpectedly. Try again."
                    watchdog.stop()
                }
            })
        }
    }

    readonly property Timer watchdog: Timer {
        interval: 45000
        onTriggered: {
            if (!root.testing)
                return
            root.phase = "error"
            root.message = "The speed test timed out. Check your connection and try again."
            runner.running = false
        }
    }
}
