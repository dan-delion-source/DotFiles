pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io
import "WaterLogic.js" as Logic

Singleton {
    id: root
    property bool ready: false
    property string error: ""
    property int filledMask: 0
    property string day: ""
    property double lastDrink: 0
    property double lastReminder: 0
    readonly property double startedAt: Date.now()
    readonly property int count: Logic.count(root.filledMask)
    readonly property bool complete: root.count === 8
    readonly property color blue: "#45bfff"
    signal goalReached()
    signal reminderRequested()

    function filled(index: int): bool { return index >= 0 && index < 8 && !!(root.filledMask & (1 << index)) }
    function checkDay(now: real): void {
        const today = Logic.dayKey(now)
        if (root.day !== today) {
            root.day = today
            root.filledMask = 0
            root.lastDrink = 0
            root.lastReminder = now
            root.save()
        }
    }
    function toggle(index: int): void {
        if (!root.ready || index < 0 || index >= 8) return
        root.checkDay(Date.now())
        const adding = !root.filled(index)
        root.filledMask ^= 1 << index
        if (adding) root.lastDrink = Date.now()
        root.save()
        if (adding && root.complete) root.goalReached()
    }
    function save(): void {
        if (!root.ready) return
        state.day = root.day
        state.mask = root.filledMask
        state.lastDrink = root.lastDrink
        state.lastReminder = root.lastReminder
        file.writeAdapter()
    }
    function restore(): void {
        root.day = state.day
        root.filledMask = Logic.cleanMask(state.mask)
        root.lastDrink = state.lastDrink
        root.lastReminder = state.lastReminder
        root.ready = true
        root.checkDay(Date.now())
    }
    function tick(now: real): void {
        if (!root.ready) return
        root.checkDay(now)
        if (!SettingsService.doNotDisturb && Logic.reminderDue(now,
                Math.max(root.startedAt, root.lastDrink, root.lastReminder), root.filledMask)) {
            root.lastReminder = now
            root.save()
            root.reminderRequested()
        }
    }
    onReminderRequested: {
        reminder.command = ["notify-send", "--app-name=Water", "--icon=dialog-information",
            "Time for a glass of water", `${root.count} of 8 glasses logged today. Open Water to log your next glass.`]
        reminder.running = true
    }
    Process { id: reminder }
    Timer { interval: 30000; repeat: true; running: root.ready; onTriggered: root.tick(Date.now()) }
    FileView {
        id: file
        path: `${SettingsService.stateDirectory}/water.json`
        onLoaded: root.restore()
        onLoadFailed: failure => {
            if (failure === FileViewError.FileNotFound) root.restore()
            else root.error = "Water progress could not be read. Check the state file before logging more glasses."
        }
        onSaveFailed: root.error = "Water progress could not be saved."
        JsonAdapter {
            id: state
            property string day: ""
            property int mask: 0
            property double lastDrink: 0
            property double lastReminder: 0
        }
    }
}
