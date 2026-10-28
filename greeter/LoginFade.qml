import QtQuick
import "./services"
import "./lock/LockStyles.js" as Styles

// Let the design open and close at its own pace. Mainframe remains visible
// through the CRT collapse; cover only its last frames before compositor exit.
Rectangle {
    id: root
    anchors.fill: parent
    color: "black"
    property real entrance: 1
    property real departure: LockService.leaving ? 1 : 0
    opacity: Math.max(root.entrance, Styles.segment(root.departure,
        LockService.activeStyle === "mainframe" ? 0.78 : 0, 1))
    Component.onCompleted: root.entrance = 0
    Behavior on entrance {
        NumberAnimation {
            duration: Styles.loginEnterMs(LockService.activeStyle, LockService.activeMotion)
            easing.type: Easing.OutCubic
        }
    }
    Behavior on departure {
        NumberAnimation {
            duration: LockService.leaving ? LockService.handoffDuration : 0
            easing.type: Easing.Linear
        }
    }
}
