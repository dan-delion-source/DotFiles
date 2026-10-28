//@ pragma ShellId yozora-greeter
//@ pragma AppId org.yozora.greeter
//@ pragma StateDir $BASE/yozora-greeter
//@ pragma CacheDir $BASE/yozora-greeter
import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Services.Greetd
import "./services"
import "./theme"
import "./lock"

ShellRoot {
    Component.onCompleted: { void SettingsService.loaded }
    Connections {
        target: SettingsService
        function onFailedChanged(): void { if (SettingsService.failed) Qt.exit(1) }
        function onLoadedChanged(): void {
            if (SettingsService.loaded && !SettingsService.preview && !Greetd.available) Qt.exit(1)
        }
    }
    Variants {
        model: SettingsService.loaded ? Quickshell.screens : []
        PanelWindow {
            id: window
            required property var modelData
            screen: modelData
            anchors { top: true; bottom: true; left: true; right: true }
            color: "black"
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
            WlrLayershell.namespace: "yozora-greeter"
            LockStyleHost {
                id: design
                anchors.fill: parent
                output: window.screen?.name ?? ""
                onSubmitted: password => LockService.submit(password)
            }
            Rectangle {
                anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 18
                width: Math.max(220, account.implicitWidth + 28); height: 38
                radius: 19; color: "#dd000000"; border.color: "#333333"
                Text {
                    id: account
                    anchors.centerIn: parent
                    text: LockService.user + " · Change user"
                    visible: !username.visible
                    font.family: Theme.fontFamily; color: "white"; font.pixelSize: 13
                }
                MouseArea {
                    anchors.fill: parent
                    onClicked: { username.visible = true; username.text = LockService.user; username.forceActiveFocus(); username.selectAll() }
                }
                TextInput {
                    id: username
                    anchors.fill: parent; anchors.margins: 10
                    visible: false; color: "white"; font.pixelSize: 14
                    maximumLength: 64
                    onAccepted: { LockService.changeUser(text); visible = false; design.claim() }
                    Keys.onEscapePressed: { visible = false; design.claim() }
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: 12
                color: "#b0ffffff"; font.family: Theme.fontFamily; font.pixelSize: 12
                text: SettingsService.preview ? "Yozora login preview · authentication disabled" : "Yozora · Hyprland"
            }
            LoginFade {}
        }
    }
}
