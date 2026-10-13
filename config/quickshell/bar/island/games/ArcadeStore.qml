import QtQuick
import Quickshell.Io
import "../../../services"

QtObject {
    id: root
    property string gameId: ""
    property string status: ""
    readonly property FileView file: FileView {
        path: `${SettingsService.stateDirectory}/${root.gameId}-save.json`
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        printErrors: false
        onSaved: root.status = "Saved"
        onSaveFailed: error => {root.status = "Save failed";console.warn(root.gameId, "save failed:", error)}
    }
    function read(): var {
        try { return JSON.parse(file.text()) } catch (error) { return null }
    }
    function save(state: var): void {file.setText(JSON.stringify(state)+"\n")}
}
