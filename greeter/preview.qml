// Run only with YOZORA_GREETER_PREVIEW=1. No session lock or login is started.
import QtQuick
import QtQuick.Window
import Quickshell
import "./services"
import "./theme"
import "./lock"
ShellRoot {
    Component.onCompleted: { if (!SettingsService.preview) Qt.exit(1) }
    Window {
        visible: SettingsService.loaded
        width: 1100; height: 700
        title: "Yozora boot login preview · authentication disabled"
        color: "black"
        LockStyleHost {
            id: host
            anchors.fill: parent
            output: "preview"
            onSubmitted: password => LockService.submit(password)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 12
            text: "Preview · authentication disabled · close this window to return"
            color: "white"; font.pixelSize: 13
        }
        onClosing: Qt.quit()
    }
    Timer {
        interval: 1500
        running: SettingsService.preview
        onTriggered: {
            if (!SettingsService.loaded || !host.ready) { restart(); return }
            console.log("YOZORA_PREVIEW_READY", SettingsService.lockStyle)
            if (Quickshell.env("YOZORA_GREETER_PREVIEW_CAPTURE") !== "")
                host.grabToImage(result => result.saveToFile(Quickshell.env("YOZORA_GREETER_PREVIEW_CAPTURE")))
        }
    }
    Timer {
        interval: 8000
        running: Quickshell.env("YOZORA_GREETER_PREVIEW_TIMEOUT") === "1"
        onTriggered: Qt.quit()
    }
}
