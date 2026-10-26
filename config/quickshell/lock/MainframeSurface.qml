import QtQuick
import "../services"
import "../theme"

Item {
    id: root
    property string output: ""
    signal submitted(string password)
    signal unavailable()

    function claim(): void { field.forceActiveFocus() }

    MainframeView {
        anchors.fill: parent
        shot: LockService.shotSource(root.output)
        account: AccountService.name
        output: root.output
        message: LockService.message
        passwordLength: LockService.typed.length
        authenticating: LockService.authenticating
        failed: LockService.failed
        leaving: LockService.leaving
        faceScanning: LockService.faceScanning
        motion: LockService.activeMotion
        ink: Theme.text
        accent: Theme.accent
        danger: Theme.red
        onUnavailable: root.unavailable()
    }

    TapHandler {
        onTapped: { LockService.rouse(); root.claim() }
    }
    TextInput {
        id: field
        objectName: "mainframePassword"
        width: 1; height: 1; opacity: 0
        enabled: !LockService.authenticating && !LockService.leaving
        echoMode: TextInput.Password
        passwordMaskDelay: 0
        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhHiddenText | Qt.ImhNoAutoUppercase
        selectByMouse: false
        text: LockService.typed
        onTextChanged: {
            if (LockService.typed !== text)
                LockService.typed = text
            if (text !== "" && LockService.failed)
                LockService.failed = false
        }
        onAccepted: {
            root.submitted(field.text)
            field.clear()
        }
        Keys.onEscapePressed: { field.clear(); LockService.rest() }
        Keys.onPressed: event => {
            if (event.key !== Qt.Key_Escape)
                LockService.rouse()
        }
        Connections {
            target: LockService
            function onTypedChanged(): void {
                if (field.text !== LockService.typed)
                    field.text = LockService.typed
            }
        }
    }
}
