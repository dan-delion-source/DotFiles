import QtQuick
import "../services"
import "LockStyles.js" as Styles

// Only the presentation changes. Session locking and authentication remain
// owned by LockScreen/LockService. A broken optional style loads Classic.
Item {
    id: root

    property string output: ""
    property string style: LockService.activeStyle
    property url mainframeSource: Qt.resolvedUrl("MainframeSurface.qml")
    property bool failed: false
    readonly property string effectiveStyle: root.failed ? "classic" : Styles.normalize(root.style)
    readonly property bool ready: surface.status === Loader.Ready
    signal submitted(string password)

    function claim(): void {
        if (surface.item)
            surface.item.claim()
    }

    onStyleChanged: root.failed = false

    Loader {
        id: surface
        anchors.fill: parent
        asynchronous: false
        source: root.effectiveStyle === "mainframe"
            ? root.mainframeSource : Qt.resolvedUrl("LockSurface.qml")
        onLoaded: Qt.callLater(root.claim)
        onStatusChanged: {
            if (status === Loader.Error && root.effectiveStyle !== "classic") {
                console.warn("Mainframe could not load; using Classic")
                root.failed = true
            }
        }
    }

    Binding {
        target: surface.item
        property: "output"
        value: root.output
        when: surface.item !== null
    }

    Connections {
        target: surface.item
        ignoreUnknownSignals: true
        function onSubmitted(password: string): void { root.submitted(password) }
        function onUnavailable(): void { root.failed = true }
    }
}
