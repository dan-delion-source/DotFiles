// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   T H E M E   S E R V I C E                                              │
// │   active palette · persistence and adaptive colours                      │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io

import "../theme"

// Owns which palette is active and keeps that choice across restarts.
QtObject {
    id: root

    readonly property string script: Quickshell.shellPath("scripts/theme_manager.py")

    property string activeId: "adaptive"
    property var dynamicColors: null
    property string error: ""

    // The adaptive entry has no static colours: they come from the wallpaper.
    readonly property var adaptiveTheme: ({
        id: "adaptive",
        name: "Matugen (Wallpaper)",
        badge: "Matugen",
        adaptive: true,
        colors: null
    })

    // Built from Palettes so a palette is described exactly once.
    readonly property var availableThemes: [root.adaptiveTheme].concat(Palettes.list)

    // The wallpaper colours once extracted, the current theme until then.
    readonly property var adaptiveSwatches: root.dynamicColors
        ? [root.dynamicColors.background, root.dynamicColors.surface,
           root.dynamicColors.accent, root.dynamicColors.text]
        : [Theme.background, Theme.surface, Theme.accent, Theme.text]

    // Restores the persisted choice on startup.
    readonly property Process stateProcess: Process {
        command: [root.script, "get-state"]
        running: true
        stdout: StdioCollector {
            // streamFinished, not textChanged: the collector fires per chunk
            // and JSON.parse on half a document throws.
            onStreamFinished: {
                const state = root.parseJson(text, "shell state")
                if (state && state.activeTheme)
                    root.setTheme(state.activeTheme, false)
            }
        }
    }

    readonly property Process extractProcess: Process {
        command: [root.script, "extract-colors"]
        onStarted: root.error = ""
        stderr: StdioCollector {
            onStreamFinished: root.error = text.trim()
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const colors = root.parseJson(text, "wallpaper colours")
                if (!colors)
                    return
                root.dynamicColors = colors
                if (root.activeId === "adaptive") {
                    Theme.apply(colors, root.adaptiveTheme.name)
                    root.pushTerminal(colors)
                }
            }
        }
    }

    readonly property Process persistProcess: Process {}

    readonly property Process terminalProcess: Process {}

    // ── FONT ────────────────────────────────────────────────────────────────
    //
    // The monospace family is pushed to kitty so the terminal follows the
    // setting.
    readonly property string terminalFont: SettingsService.fontMono

    onTerminalFontChanged: root.pushTerminalFont()

    function pushTerminalFont(): void {
        root.fontProcess.command = [root.script, "push-terminal-font",
                                    SettingsService.fontMono]
        root.fontProcess.running = true
    }

    readonly property Process fontProcess: Process {}

    // Also pushed at startup: if the setting never changes, the fragment
    // kitty.conf includes would never be written.
    Component.onCompleted: {
        root.pushTerminalFont()
        root.pushGreeting()
        root.refreshGreetings()
    }

    // ── GREETING ────────────────────────────────────────────────────────────
    //
    // Which scene `fa` shows. The palette push redraws all of them
    // (`greeting.py`); this only records the choice. `random` is resolved
    // by `fa`.
    property var greetings: [
        { id: "lava", label: "Lava lamp", kind: "scene" },
        { id: "critters", label: "Critters", kind: "scene" },
        { id: "koi", label: "Koi", kind: "scene" },
        { id: "invaders", label: "Invaders", kind: "scene" },
        { id: "random", label: "Random", kind: "scene" }
    ]
    readonly property bool refreshingGreetings: greetingScan.running
    property bool greetingsLoaded: false
    property string greetingScanError: ""
    property string greetingApplyError: ""
    property string greetingScanStatus: ""
    readonly property bool greetingUnavailable: root.greetingsLoaded &&
        !root.greetings.some(entry => entry.id === SettingsService.greeting)

    function refreshGreetings(): void {
        if (!root.refreshingGreetings)
            root.greetingScan.running = true
    }

    readonly property Process greetingScan: Process {
        command: [root.greetingScript, "list"]
        onStarted: {
            root.greetingScanError = ""
            root.greetingScanStatus = ""
        }
        onExited: exitCode => {
            if (exitCode !== 0)
                root.greetingScanError = "Could not scan greetings. Check access to the Fastfetch logos folder."
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (text.trim())
                    console.warn(text.trim())
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const list = root.parseJson(text, "greeting library")
                if (Array.isArray(list)) {
                    root.greetings = list
                    root.greetingsLoaded = true
                    root.greetingScanStatus = `${list.filter(entry => entry.kind !== "scene").length} logo files available`
                }
            }
        }
    }

    readonly property string greetingScript: Quickshell.shellPath("scripts/greeting.py")
    readonly property string greeting: SettingsService.greeting

    onGreetingChanged: root.pushGreeting()

    // A running Process ignores being started again, so queue the latest
    // pick.
    property bool greetingPending: false

    function pushGreeting(): void {
        if (!SettingsService.arrived)
            return
        if (root.greetingProcess.running) {
            root.greetingPending = true
            return
        }
        root.greetingProcess.command = [root.greetingScript, "choose", SettingsService.greeting]
        root.greetingProcess.running = true
    }

    readonly property Connections greetingSettingsReady: Connections {
        target: SettingsService
        function onArrivedChanged(): void {
            if (SettingsService.arrived)
                root.pushGreeting()
        }
    }

    readonly property Process greetingProcess: Process {
        onStarted: root.greetingApplyError = ""
        stderr: StdioCollector {
            onStreamFinished: root.greetingApplyError = text.trim()
        }
        onExited: {
            if (root.greetingPending) {
                root.greetingPending = false
                root.pushGreeting()
            }
        }
    }

    // Written by `greeting.py` once every scene is redrawn. The settings
    // tiles reload on this rather than on the palette change, when the new
    // scenes are still being drawn.
    property string greetingStamp: ""

    readonly property FileView greetingStampView: FileView {
        path: `${SettingsService.stateDirectory}/greeting.stamp`
        watchChanges: true
        onFileChanged: reload()
        onLoaded: root.greetingStamp = text().trim()
    }

    // The backend writes the colour fragment kitty.conf includes and repaints
    // open kitty windows.
    function pushTerminal(colors: var): void {
        if (!colors)
            return
        root.terminalProcess.command = [root.script, "push-terminal-palette",
                                        JSON.stringify(colors)]
        root.terminalProcess.running = true
    }

    function parseJson(text: string, what: string): var {
        if (!text || text.trim() === "")
            return null
        try {
            return JSON.parse(text)
        } catch (error) {
            console.warn(`Cannot parse ${what}:`, error)
            return null
        }
    }

    function reloadAdaptiveColors(): void {
        root.extractProcess.running = true
    }

    function setTheme(themeId: string, persist = true): void {
        root.activeId = themeId
        Theme.activeId = themeId

        if (themeId === "adaptive") {
            if (root.dynamicColors) {
                Theme.apply(root.dynamicColors, root.adaptiveTheme.name)
                root.pushTerminal(root.dynamicColors)
            } else {
                root.reloadAdaptiveColors()
            }
        } else {
            const palette = Palettes.byId(themeId)
            if (palette) {
                Theme.apply(palette.colors, palette.name)
                root.pushTerminal(palette.colors)
            } else {
                console.warn("Unknown palette:", themeId)
            }
        }

        if (persist) {
            root.persistProcess.command = [root.script, "set-theme", themeId]
            root.persistProcess.running = true
        }
    }
}
