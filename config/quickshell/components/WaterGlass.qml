import QtQuick
import QtQuick.Controls as QQC
import "../theme"

QQC.AbstractButton {
    id: root
    property bool drank: false
    property bool interactive: true
    property int number: 0
    property real level: drank ? 1 : 0
    readonly property color waterBlue: "#45bfff"
    signal activated()
    implicitWidth: 64
    implicitHeight: 82
    enabled: interactive
    focusPolicy: interactive ? Qt.StrongFocus : Qt.NoFocus
    Accessible.name: `Glass ${number}${drank ? ", logged; click to undo" : ", empty; click to log"}`
    onClicked: root.activated()
    onLevelChanged: drawing.requestPaint()
    onDrankChanged: drawing.requestPaint()
    Behavior on level { NumberAnimation { duration: 480 * Theme.motion; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: 10
        color: root.hovered && root.interactive ? Theme.surfaceHover : "transparent"
        border.width: root.visualFocus ? 1 : 0
        border.color: root.waterBlue
    }
    contentItem: Canvas {
        id: drawing
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const w = width, h = height
            function outline() {
                ctx.beginPath()
                ctx.moveTo(w * 0.18, h * 0.12)
                ctx.lineTo(w * 0.82, h * 0.12)
                ctx.lineTo(w * 0.70, h * 0.89)
                ctx.quadraticCurveTo(w * 0.50, h * 0.94, w * 0.30, h * 0.89)
                ctx.closePath()
            }
            if (root.level > 0) {
                ctx.save()
                outline(); ctx.clip()
                const y = h * (0.91 - 0.65 * root.level)
                const wave = h * 0.055 * Math.sin(root.level * Math.PI)
                ctx.beginPath(); ctx.moveTo(0, y)
                ctx.quadraticCurveTo(w * 0.25, y - wave, w * 0.5, y)
                ctx.quadraticCurveTo(w * 0.75, y + wave, w, y)
                ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath()
                ctx.fillStyle = root.waterBlue; ctx.globalAlpha = 0.8
                ctx.fill(); ctx.restore()
            }
            outline()
            ctx.lineWidth = Math.max(1.4, w * 0.025)
            ctx.strokeStyle = root.drank ? root.waterBlue : Theme.textMuted
            ctx.stroke()
        }
    }
}
