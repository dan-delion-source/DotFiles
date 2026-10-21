import QtQuick
import Quickshell.Io
import "../../../services"

QtObject {
    id: root
    property string status: ""
    readonly property FileView file: FileView {
        path: `${SettingsService.stateDirectory}/neon-breakout-save.json`
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        printErrors: false
        onSaved: root.status = "SAVED"
        onSaveFailed: error => {
            root.status = "SAVE FAILED"
            console.warn("Neon Breakout save failed:", error)
        }
    }
    function read(): var {
        try { return JSON.parse(file.text()) } catch (error) { return null }
    }
    function save(state: var): void { file.setText(JSON.stringify(state) + "\n") }
}
