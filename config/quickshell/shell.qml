// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S H E L L                                                              │
// │   quickshell entry point · windows and top-level wiring                  │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

// Greyscale text: subpixel edges assume an opaque ground and fringe on a
// transparent surface.
//@ pragma ShellId danshell
//@ pragma AppId org.danshell
//@ pragma StateDir $BASE/danshell
//@ pragma DataDir $BASE/danshell
//@ pragma CacheDir $BASE/danshell
//@ pragma Env QSG_DISTANCEFIELD_ANTIALIASING=gray

import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io

import "./bar"
import "./capture"
import "./desktop"
import "./lock"
import "./services"
import "./settings"

// Entry point: the windows, the services that must start at boot, and the
// wiring between services that may not reference each other.
ShellRoot {
    id: root

    // Singletons are built on first use. Each of these has to be running from
    // boot, not from the moment a panel first reads it.
    Component.onCompleted: {
        // Restores the saved palette.
        void ThemeService.activeId
        // Builds the launcher index ahead of the first open.
        void LauncherService.applications
        // Keeps history, so the graph has data before the panel opens.
        void StatsService.ready
        // Re-applies the animation preset and every other overridden
        // Hyprland option.
        void CompositorService.animationPreset
        // Re-applies the monitor arrangement kept for this set of screens.
        void MonitorService.loaded
        // Writes the profile's keys to keys.tsv for keybinds.lua.
        void ShortcutService.catalogue
        // Reads the user's name and face ahead of the first lock.
        void AccountService.user
        // Probes for hyprpicker, so the first press is not the one that asks.
        void PickerService.available
        // Starts the clipboard watcher.
        void ClipboardService.count
        // Probes the monitor source, so the first take is not silent, and
        // picks up a take left running by a previous shell.
        void RecorderService.available
        // Restores the night light.
        void SunsetService.available
        // Arms the idle monitors.
        void IdleService.lockAfter
        // Holds every sleep until the lock is up.
        void SessionService.sleepPending
        // Seeds the example profiles on a first install.
        void ProfileService.arrived
    }

    // ── SCREENS ─────────────────────────────────────────────────────────────
    //
    // Every surface is a Variants over the screens. A PanelWindow whose
    // ShellScreen is destroyed (output unplugged) does not recover when handed
    // a new one; Variants destroys and rebuilds the window with the list,
    // which does.

    // Follow the primary selected in Settings → Monitors; hotplug falls back
    // to an available display without assuming a connector or laptop panel.
    readonly property string barScreenName: MonitorService.effectivePrimaryName

    // The live island is free to open on any screen. Open panels retain their
    // host until closed; the fixed bar remains visible on its own screen.
    property string islandName: root.barScreenName
    readonly property string wantedIslandName: {
        for (const screen of Quickshell.screens)
            if (screen.name === HyprlandService.focusedMonitor)
                return screen.name
        return root.barScreenName
    }
    onWantedIslandNameChanged: root.settleIsland()

    function settleIsland(): void {
        root.claimIsland(root.wantedIslandName)
    }

    // A bar saying the pointer is on it (`Bar.claimed`), which is the same
    // answer the compositor's focus gives a moment earlier — except when the
    // pointer was warped there rather than walked.
    function claimIsland(name: string): void {
        if (name === "" || root.islandName === name || (root.island?.expanded ?? false))
            return
        root.islandName = name
    }

    readonly property Connections islandRests: Connections {
        target: root.island

        function onExpandedChanged(): void {
            root.settleIsland()
        }
    }

    // `islandName` with a screen that is not plugged in resolved away, so an
    // output leaving never leaves every bar inert.
    readonly property string liveScreenName: {
        for (const screen of Quickshell.screens)
            if (screen.name === root.islandName)
                return root.islandName
        return MonitorService.effectivePrimaryName
    }

    // The live bar's island. Notifiable through `instances` and through each
    // bar's own `live`, so it follows the flag rather than a window.
    readonly property var island: {
        for (const bar of bars.instances)
            if (bar.live)
                return bar.island
        return null
    }

    // Query the actual pointer, rather than assuming keyboard focus follows it.
    property string pendingPanel: ""
    property bool pendingToggle: false

    function routePanel(panel: string, toggle: bool): void {
        // Keep a running game/panel on its host, including nested navigation.
        if (root.island?.expanded) {
            if (toggle) root.island.toggle(panel)
            else root.island.open(panel)
            return
        }
        root.pendingPanel = panel
        root.pendingToggle = toggle
        pointerTimeout.restart()
        if (!pointerProbe.running)
            pointerProbe.running = true
    }

    function togglePanel(panel: string): void {
        root.routePanel(panel, true)
    }

    function openPanel(panel: string): void {
        root.routePanel(panel, false)
    }

    function finishRoute(name: string): void {
        if (root.pendingPanel === "")
            return
        pointerTimeout.stop()
        const panel = root.pendingPanel
        const toggle = root.pendingToggle
        root.pendingPanel = ""
        const found = Quickshell.screens.find(screen => screen.name === name)
        root.claimIsland(found ? name : root.wantedIslandName)
        // Allow Variants/Bindings to transfer active status before opening.
        Qt.callLater(() => {
            if (toggle) root.island?.toggle(panel)
            else root.island?.open(panel)
        })
    }

    Process {
        id: pointerProbe

        command: ["python3", "-c", [
            "import json, subprocess",
            "try:",
            "    p = json.loads(subprocess.check_output(['hyprctl', '-j', 'cursorpos'], timeout=2))",
            "    monitors = json.loads(subprocess.check_output(['hyprctl', '-j', 'monitors'], timeout=2))",
            "    for m in monitors:",
            "        if m.get('disabled', False): continue",
            "        w, h = m['width'], m['height']",
            "        if m.get('transform', 0) % 2: w, h = h, w",
            "        scale = m.get('scale', 1) or 1",
            "        if m['x'] <= p['x'] < m['x'] + w / scale and m['y'] <= p['y'] < m['y'] + h / scale:",
            "            print(m['name']); break",
            "except Exception:",
            "    pass"
        ].join("\n")]

        stdout: StdioCollector {
            onStreamFinished: root.finishRoute(this.text.trim())
        }
        onExited: Qt.callLater(() => {
            // Give stdout's completion handler priority over fallback routing.
            if (root.pendingPanel !== "")
                root.finishRoute("")
        })
    }

    Timer {
        id: pointerTimeout
        interval: 5000
        onTriggered: root.finishRoute("")
    }

    // ── BARS ────────────────────────────────────────────────────────────────
    //
    // One bar per screen, exactly one of them live. A layer surface cannot
    // change output, so an island that moved would be a bar built from
    // nothing on the far screen, its clock and workspaces animating in over
    // the same drawing. Every screen carrying the whole bar, with one flag
    // deciding which is live, costs one transparent surface per screen and no
    // frames at all.

    // The space the bars keep, held per screen and never rebuilt, so swapping
    // one kind of bar for another moves no windows.
    Variants {
        model: Quickshell.screens.filter(screen => screen.name === root.barScreenName)

        BarReserve {
            required property var modelData

            screen: modelData
        }
    }

    Variants {
        id: bars

        model: Quickshell.screens

        Bar {
            required property var modelData

            screen: modelData
            live: modelData.name === root.liveScreenName
            barVisible: modelData.name === root.barScreenName

            onClaimed: root.claimIsland(modelData.name)
        }
    }

    // Widgets under the windows, on every screen: a row carries the screen it
    // is on, and every board has a grid of its own.
    Variants {
        model: Quickshell.screens

        Desktop {
            required property var modelData

            screen: modelData
        }
    }

    // Notes docked on the screen edges, on every screen, for the desktop's
    // reason. A deck is a row like a widget and carries its screen too.
    Variants {
        model: Quickshell.screens

        Deck {
            required property var modelData

            screen: modelData
        }
    }

    // A normal window rather than an island panel, so the island stays
    // visible while its settings change.
    SettingsWindow {
        id: settingsWindow

        // The palette and wallpaper pickers live on the island.
        onPanelRequested: panel => root.openPanel(panel)
    }

    // The control centre's gear. The island has already closed itself.
    Connections {
        target: root.island

        function onSettingsRequested(): void {
            settingsWindow.open()
        }
    }

    Connections {
        target: DesktopService

        function onSettingsRequested(): void {
            root.island?.close()
            settingsWindow.open()
        }
    }

    // The bar's settings button, which closes the window it opened.
    Connections {
        target: ModuleService

        function onSettingsRequested(): void {
            root.toggleSettings()
        }
    }

    // Optional clipboard wipe on lock. Joined here so neither service depends
    // on the other. Password-manager copies are never stored in the first
    // place; this covers everything else.
    Connections {
        target: LockService

        function onLockedChanged(): void {
            if (LockService.locked && SettingsService.clipboardWipeOnLock)
                ClipboardService.wipe()
        }
    }

    // ext-session-lock. The bar is not on screen while it is up.
    LockScreen {}

    // The lock screenshots the desktop before covering it, so it waits until
    // the island is collapsed and settled.
    Binding {
        target: LockService
        property: "shellQuiet"
        value: !root.island || (!root.island.expanded && root.island.settled)
    }

    // Global shortcuts: keybinds.lua binds a key to the name, and the action
    // lives here, so a new panel needs no compositor config.
    GlobalShortcut {
        appid: "danshell"
        name: "launcher"
        description: "Open the island launcher"
        onPressed: root.togglePanel("launcher")
    }

    // ── LID ─────────────────────────────────────────────────────────────────
    //
    // Handled here rather than with `switch:` binds in Lua. MonitorService's
    // display profile is the one owner of whether the panel is lit, and it is
    // re-applied on hotplug and after config reloads. A `switch:` bind in the
    // same file as `hl.monitor()` calls is also silently not registered, and
    // a runtime monitor rule does not survive a reload.
    GlobalShortcut {
        appid: "danshell"
        name: "lidClosed"
        description: "The laptop lid was closed"
        onPressed: MonitorService.lid(true)
    }

    // Opening the lid is somebody sitting down: it wakes the lock, which
    // looks for them.
    GlobalShortcut {
        appid: "danshell"
        name: "lidOpened"
        description: "The laptop lid was opened"
        onPressed: {
            MonitorService.lid(false)
            LockService.rouse()
        }
    }

    GlobalShortcut {
        appid: "danshell"
        name: "controls"
        description: "Open the island quick controls"
        onPressed: root.togglePanel("controls")
    }

    // The brightness keys act on the focused screen, which only the shell
    // knows how to dim. A held key repeats the press.
    GlobalShortcut {
        appid: "danshell"
        name: "brightnessUp"
        description: "Raise the focused screen's brightness"
        onPressed: BrightnessService.step(5)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "brightnessDown"
        description: "Lower the focused screen's brightness"
        onPressed: BrightnessService.step(-5)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "overview"
        description: "Open the workspace overview"
        onPressed: root.togglePanel("overview")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "stats"
        description: "Open the system statistics"
        onPressed: root.togglePanel("stats")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "session"
        description: "Open the session menu"
        onPressed: root.togglePanel("session")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "lock"
        description: "Lock the screen"
        onPressed: LockService.lock()
    }

    // An open panel holds the keyboard exclusively, which beats a normal
    // window, so the island closes first or the window cannot be typed in.
    function toggleSettings(): void {
        if (!settingsWindow.shown)
            root.island?.close()
        settingsWindow.toggle()
    }

    GlobalShortcut {
        appid: "danshell"
        name: "settings"
        description: "Open the settings window"
        onPressed: root.toggleSettings()
    }

    GlobalShortcut {
        appid: "danshell"
        name: "appearance"
        description: "Open the island appearance panel"
        onPressed: root.togglePanel("appearance")
    }

    // Same panel, on the palette strip. Each name only closes from its own
    // strip.
    GlobalShortcut {
        appid: "danshell"
        name: "palette"
        description: "Open the island appearance panel on the palettes"
        onPressed: root.togglePanel("palette")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "pet"
        description: "Open the pet"
        onPressed: root.togglePanel("pet")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "games"
        description: "Open the games"
        onPressed: root.togglePanel("games")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "notes"
        description: "Open the notes"
        onPressed: root.togglePanel("notes")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "board"
        description: "Open the task board"
        onPressed: root.togglePanel("board")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "keys"
        description: "Show every key"
        onPressed: root.togglePanel("keys")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "zen"
        description: "Hide or show the bar"
        onPressed: SettingsService.set("barHidden", !SettingsService.barHidden)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "widgets"
        description: "Hide or show the desktop widgets"
        onPressed: SettingsService.set("desktopHidden", !SettingsService.desktopHidden)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "packages"
        description: "Open the packages"
        onPressed: root.togglePanel("packages")
    }

    // The clipboard and the emoji are launcher modes: pressed again on that
    // mode it closes, pressed on another mode it switches. The query is set
    // before opening because with `launcherFits` the panel's height depends on
    // it, and the island is sized before the panel exists.
    function openLauncherOn(mode: string): void {
        const sigil = SettingsService.launcherPrefix(mode)
        const showing = root.island?.state.openPanel === "launcher"
        if (showing && LauncherService.query.startsWith(sigil)) {
            root.island?.close()
            return
        }
        LauncherService.query = sigil
        root.openPanel("launcher")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "clipboard"
        description: "Open the launcher on the clipboard"
        onPressed: root.openLauncherOn("clipboard")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "emoji"
        description: "Open the launcher on the emoji"
        onPressed: root.openLauncherOn("emoji")
    }

    // hyprpicker freezes a screenshot of the screen, so an open panel has to
    // finish closing before it starts.
    GlobalShortcut {
        appid: "danshell"
        name: "picker"
        description: "Pick a colour off the screen"
        onPressed: {
            const wasOpen = root.island?.expanded ?? false
            root.island?.close()
            PickerService.pick(wasOpen ? PickerService.settle : 0)
        }
    }

    // ── CAPTURE ─────────────────────────────────────────────────────────────
    //
    // `capture` opens the surface in its last mode; the others preset a shape
    // or destination and are unbound by default. The photo is taken with
    // whatever panel is open, so a panel can be captured.
    function capture(shape: string, to: string): void {
        CaptureService.open(shape, "photo", to, 0)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "capture"
        description: "Open the capture surface"
        onPressed: CaptureService.open("", "", "", 0)
    }

    GlobalShortcut {
        appid: "danshell"
        name: "captureRegion"
        description: "Capture a region"
        onPressed: root.capture("region", "file")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "captureWindow"
        description: "Capture a window"
        onPressed: root.capture("window", "file")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "captureScreen"
        description: "Capture the whole screen"
        onPressed: root.capture("screen", "file")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "captureEdit"
        description: "Capture a region and annotate it"
        onPressed: root.capture("region", "editor")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "captureText"
        description: "Read a region as text"
        onPressed: root.capture("region", "text")
    }

    GlobalShortcut {
        appid: "danshell"
        name: "record"
        description: "Start or stop recording the screen"
        onPressed: {
            root.island?.close()
            RecorderService.toggle()
        }
    }

    // Always built rather than behind a Loader: creating a layer surface at
    // capture time flashes a black frame over the screen being captured.
    CaptureOverlay {}

    // Region recording, joined here to keep the two services acyclic.
    Connections {
        target: CaptureService

        function onRecordRequested(shape: string, geometry: string): void {
            RecorderService.startAt(shape, geometry)
        }
    }

    // A new wallpaper re-derives the adaptive palette. Wired here so the
    // dependency runs one way: the theme knows about wallpapers, not the
    // reverse.
    Connections {
        target: WallpaperService

        function onApplied(path: string): void {
            ThemeService.reloadAdaptiveColors()
        }
    }

    // ── IPC ─────────────────────────────────────────────────────────────────
    //
    // Every palette push hangs off WallpaperService.applied, which only fires
    // inside this process. External callers (Thunar's "Set as Wallpaper")
    // come in here instead of running theme_manager.py directly:
    //   qs ipc --path /path/to/this/quickshell call wallpaper set <path>
    IpcHandler {
        target: "wallpaper"

        function set(path: string): string {
            if (!path)
                return "usage: qs ipc --path /path/to/this/quickshell call wallpaper set <path>"
            WallpaperService.apply(path)
            return path
        }
    }

    // `./setup sync` calls this once every file has landed. The reload the
    // shell starts on its own when a file changes can begin before the last
    // one is written, and then never sees it:
    //   qs ipc --path /path/to/this/quickshell call shell reload
    // The same two switches as the keys, for anything else to bind.
    IpcHandler {
        target: "bar"

        function toggle(): void {
            SettingsService.set("barHidden", !SettingsService.barHidden)
        }
    }

    IpcHandler {
        target: "widgets"

        function toggle(): void {
            SettingsService.set("desktopHidden", !SettingsService.desktopHidden)
        }
    }

    IpcHandler {
        target: "shell"

        function reload(): void {
            Quickshell.reload(false)
        }
    }

}
