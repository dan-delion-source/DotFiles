import QtQuick
import "../../components"
import "../../services"
import "../../theme"

// A decorative, independently placeable bar module. Reuses the existing
// system watcher so it needs neither Zenith's daemon nor a new sampler.
RunningCat {
    id: root
    size: Theme.capsuleHeight * 35 / 30
    profile: SystemService.powerProfile
    lively: SettingsService.motionScale > 0
    property bool completed: false
    property bool watching: false

    function updateWatch(): void {
        const wanted = root.completed && root.visible && root.lively
        if (wanted === root.watching)
            return
        root.watching = wanted
        if (wanted) SystemService.subscribe()
        else SystemService.release()
    }
    onVisibleChanged: root.updateWatch()
    onLivelyChanged: root.updateWatch()
    Component.onCompleted: { root.completed = true; root.updateWatch() }
    Component.onDestruction: if (root.watching) SystemService.release()
}
