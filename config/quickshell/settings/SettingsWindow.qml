// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S E T T I N G S   W I N D O W                                          │
// │   settings window · a regular, movable window                            │
// │                                                                          │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import Quickshell
import Quickshell.Io

import "../theme"

// Settings is a window rather than an island panel, so the bar and island stay
// visible and react live while their own settings change.
//
// It is an xdg-shell toplevel, not a layer surface: Hyprland moves, resizes,
// focuses and closes it like any other window, and draws its rounding and
// shadow. `windowrules.lua` floats it when that Hyprland config is loaded;
// the scoped helper covers sessions using another Hyprland config.
FloatingWindow {
    id: root
    reloadableId: "danshell-settings"

    // Kept in sync with `visible` both ways, so closing the window from the
    // compositor resets it and it can be opened again.
    property bool shown: false
    property bool contentReady: false
    property bool floatAgain: false

    function open(): void { root.shown = true }
    function close(): void { root.shown = false }
    function toggle(): void { root.shown = !root.shown }

    // Island panels are opened by the shell, not by this window.
    signal panelRequested(string panel)

    // Matched by the window rule in `windowrules.lua`.
    title: "Settings"

    implicitWidth: 900
    implicitHeight: 620
    minimumSize: Qt.size(760, 520)

    color: "#000000"
    surfaceFormat.opaque: true
    mask: null
    visible: root.shown

    onVisibleChanged: {
        root.contentReady = false
        geometrySettle.stop()
        if (!root.visible) {
            root.floatAgain = false
            if (root.shown) root.shown = false
        } else {
            if (floatProcess.running) root.floatAgain = true
            else floatProcess.running = true
        }
    }

    Process {
        id: floatProcess
        command: [Quickshell.shellPath("scripts/float_settings.py"),
                  "--pid", String(Quickshell.processId)]
        onExited: {
            if (!root.visible) return
            if (root.floatAgain) {
                root.floatAgain = false
                floatProcess.running = true
            } else geometrySettle.restart()
        }
    }

    // Paint the full surface immediately, including while the panel is waiting
    // for its initial compositor geometry. An empty scene can remain unpainted.
    Rectangle { anchors.fill: parent; color: Theme.background }

    // Map and float first. Building the animated page while the compositor is
    // still changing its initial size can leave a stale clipped render area.
    Timer {
        id: geometrySettle
        interval: 50
        onTriggered: if (root.visible) root.contentReady = true
    }
    onWidthChanged: {
        if (root.visible && !root.contentReady && !floatProcess.running)
            geometrySettle.restart()
    }
    onHeightChanged: {
        if (root.visible && !root.contentReady && !floatProcess.running)
            geometrySettle.restart()
    }

    // Built on open and destroyed on close, so pages query state when created
    // and release their subscriptions when gone.
    Loader {
        id: panelLoader
        objectName: "settingsPanelLoader"
        anchors.fill: parent
        active: root.visible && root.contentReady
        sourceComponent: panel
    }

    Component {
        id: panel

        SettingsPanel {
            onClosed: root.close()
            onPanelRequested: name => root.panelRequested(name)
        }
    }

}
