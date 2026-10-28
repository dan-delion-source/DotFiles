import QtQuick
import "LockStyles.js" as Styles

// Presentation only: no service imports, input fields, PAM, or session locks.
// MainframeSurface supplies live state; settings supply inert preview values.
// CRT direction and shader adapted from dhrruvsharma/shell (GPL-3.0-or-later).
Item {
    id: root

    property url shot
    property string account: ""
    property string output: ""
    property string message: ""
    property int passwordLength: 0
    property bool authenticating: false
    property bool failed: false
    property bool leaving: false
    property bool faceScanning: false
    property bool preview: false
    property real motion: 1
    property color ink: "#cdd6f4"
    property color accent: "#89b4fa"
    property color danger: "#f38ba8"
    property string mono: "Iosevka Nerd Font"
    readonly property string terminalFont: {
        const installed = Qt.fontFamilies()
        const candidates = [root.mono, "JetBrainsMono Nerd Font Mono", "JetBrains Mono",
                            "DejaVu Sans Mono", "Liberation Mono"]
        return candidates.find(name => installed.indexOf(name) >= 0) ?? "monospace"
    }
    property url shader: Qt.resolvedUrl("shaders/mainframe-crt.frag.qsb")
    signal unavailable()
    readonly property bool effectsEnabled: GraphicsInfo.api !== GraphicsInfo.Software
    readonly property color displayInk: root.ink.hslLightness < 0.65
        ? Qt.hsla(root.ink.hslHue, Math.min(0.3, root.ink.hslSaturation), 0.85, 1) : root.ink
    readonly property color displayAccent: root.accent.hslLightness < 0.65
        ? Qt.hsla(root.accent.hslHue, root.accent.hslSaturation, 0.78, 1) : root.accent
    readonly property color displayDanger: root.danger.hslLightness < 0.6
        ? Qt.hsla(root.danger.hslHue, root.danger.hslSaturation, 0.75, 1) : root.danger

    property real intro: root.preview || root.motion === 0 ? 1 : root.loginMode ? 0.46 : 0
    property real outro: 0
    property real elapsed: 0
    property date now: new Date()
    readonly property real speed: Styles.motionFactor(root.motion)
    readonly property int entranceDuration: root.loginMode
        ? Styles.loginEnterMs("mainframe", root.speed) : Math.round(1350 * root.speed)
    readonly property int departureDuration: root.loginMode
        ? Styles.loginExitMs("mainframe", root.speed) : Styles.exitMs("mainframe", root.speed)
    readonly property real scaleFactor: Math.min(root.width / 1920, root.height / 1080)
    readonly property real textIn: Styles.segment(root.intro, 0.62, 1)
    property bool loginMode: false
    readonly property var bootLines: [
        "[ SESSION ]  " + (root.loginMode ? "YOZORA SYSTEM LOGIN" : "SESSION LOCK ENGAGED"),
        "[ ACCOUNT ]  " + root.account,
        "[ DISPLAY ]  " + root.output,
        "[ INPUT   ]  PASSWORD AUTHENTICATION"
    ]
    readonly property string logText: root.bootLines.join("\n").slice(
        0, Math.ceil(root.bootLines.join("\n").length * root.textIn))
    readonly property string statusText: root.leaving ? "ACCESS GRANTED"
        : root.authenticating ? "VERIFYING CREDENTIALS…"
        : root.message !== "" ? root.message
        : root.faceScanning ? "FACE AUTHENTICATION IN PROGRESS…" : "ENTER PASSWORD TO CONTINUE"

    function start(): void {
        if (!root.preview && root.speed > 0)
            opening.restart()
    }
    Component.onCompleted: root.start()
    onLeavingChanged: {
        if (root.leaving) {
            opening.stop()
            root.intro = 1
            if (root.speed === 0)
                root.outro = 1
            else
                closing.restart()
        } else {
            // Authentication/launch cancellation can interrupt a slow login
            // outro. Restore the terminal so another attempt stays usable.
            closing.stop()
            root.outro = 0
        }
    }
    onMotionChanged: {
        if (root.speed === 0) {
            opening.stop()
            closing.stop()
            root.intro = 1
            root.outro = root.leaving ? 1 : 0
        }
    }

    NumberAnimation {
        id: opening
        target: root
        property: "intro"
        // Login has no desktop fold before the terminal: start directly at
        // power-on so a slower entrance does not add a blank first second.
        from: root.loginMode ? 0.46 : 0; to: 1
        duration: root.entranceDuration
    }
    NumberAnimation {
        id: closing
        target: root
        property: "outro"
        from: 0; to: 1
        duration: root.departureDuration
    }
    Timer {
        interval: 1000
        running: root.visible && !root.preview
        repeat: true
        onTriggered: root.now = new Date()
    }
    Timer {
        interval: 100
        running: root.visible && !root.preview && root.speed > 0
        repeat: true
        onTriggered: root.elapsed += 0.1
    }

    Rectangle { anchors.fill: parent; color: "#06090a" }

    Image {
        id: desktop
        anchors.fill: parent
        // Boot login has no desktop behind it. Avoid decoding a full-size
        // wallpaper merely to reveal it before the greeter compositor exits.
        source: root.loginMode ? "" : root.shot
        fillMode: Image.PreserveAspectCrop
        visible: false
        cache: false
    }

    ShaderEffectSource {
        id: desktopTexture
        sourceItem: desktop
        hideSource: true
        live: false
    }

    // The captured desktop folds into a line and dot on entry, and is
    // revealed on exit. Missing images simply leave the opaque black ground.
    ShaderEffect {
        anchors.fill: parent
        visible: !root.loginMode && root.effectsEnabled && desktop.status === Image.Ready && (!root.preview || root.outro > 0)
        opacity: root.leaving ? Styles.segment(root.outro, 0.38, 1)
            : 1 - Styles.segment(root.intro, 0.46, 0.62)
        property variant source: desktopTexture
        property real itemWidth: Math.max(1, width)
        property real itemHeight: Math.max(1, height)
        property real crt: root.leaving ? 1 - root.outro : Styles.segment(root.intro, 0, 0.2)
        property real bloom: 0
        property real squashY: root.leaving ? Styles.segment(root.outro, 0.48, 1)
            : 1 - Styles.segment(root.intro, 0.17, 0.38)
        property real squashX: root.leaving ? Styles.segment(root.outro, 0.38, 0.65)
            : 1 - Styles.segment(root.intro, 0.38, 0.55)
        property real flash: 0
        property real glitch: 0
        property real time: root.elapsed
        fragmentShader: root.shader
        onStatusChanged: if (status === ShaderEffect.Error) root.unavailable()
    }

    Item {
        id: terminalPlane
        objectName: "mainframeTerminal"
        anchors.fill: parent
        layer.enabled: root.effectsEnabled
        layer.effect: ShaderEffect {
            property variant source
            property real itemWidth: Math.max(1, terminalPlane.width)
            property real itemHeight: Math.max(1, terminalPlane.height)
            property real crt: 1
            property real bloom: 0.28
            property real squashY: root.leaving ? 1 - (root.loginMode
                ? Styles.segment(root.outro, 0.12, 0.78) : Styles.segment(root.outro, 0, 0.30))
                : Styles.segment(root.intro, 0.54, 0.80)
            property real squashX: root.leaving ? 1 - (root.loginMode
                ? Styles.segment(root.outro, 0.70, 0.94) : Styles.segment(root.outro, 0.26, 0.44))
                : Styles.segment(root.intro, 0.48, 0.63)
            property real flash: 0
            property real glitch: root.failed && root.speed > 0 ? 0.15 : 0
            property real time: root.elapsed
            fragmentShader: root.shader
            onStatusChanged: if (status === ShaderEffect.Error) root.unavailable()
        }
        opacity: root.leaving ? 1 - (root.loginMode
            ? Styles.segment(root.outro, 0.90, 1) : Styles.segment(root.outro, 0.32, 0.48))
            : Styles.segment(root.intro, 0.46, 0.60)

        Rectangle { anchors.fill: parent; color: "#06090a" }
        Item {
            width: 1920; height: 1080
            anchors.centerIn: parent
            scale: root.scaleFactor

            Rectangle { x: 64; y: 64; width: 1792; height: 1; color: root.displayAccent; opacity: 0.45 }
            Text {
                x: 64; y: 80; width: 1270
                text: root.logText
                textFormat: Text.PlainText
                font.family: root.terminalFont
                font.pixelSize: 19
                lineHeight: 1.5
                color: root.displayAccent
                elide: Text.ElideRight
            }
            Text {
                x: 1390; y: 80; width: 466
                text: Qt.formatDateTime(root.now, "dddd, dd MMM yyyy").toUpperCase()
                textFormat: Text.PlainText
                horizontalAlignment: Text.AlignRight
                font.family: root.terminalFont; font.pixelSize: 17
                color: root.displayInk
            }
            Text {
                x: 1390; y: 118; width: 466
                text: "MAINFRAME / SESSION LOCK"
                horizontalAlignment: Text.AlignRight
                font.family: root.terminalFont; font.pixelSize: 15
                color: root.displayAccent
            }
            MainframeClock {
                x: (1920 - width) / 2; y: 470
                time: Qt.formatTime(root.now, "HH:mm")
                ink: root.displayInk
            }
            Text {
                x: 310; y: 610; width: 1300
                text: root.statusText
                textFormat: Text.PlainText
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                font.family: root.terminalFont; font.pixelSize: 20
                color: root.failed ? root.displayDanger : root.displayAccent
            }
            Text {
                x: 310; y: 674; width: 1300
                text: "Password: " + "*".repeat(Math.max(0, Math.min(36, root.passwordLength)))
                    + (root.passwordLength > 36 ? "…" : "")
                    + (root.preview || root.speed === 0 || Math.floor(root.elapsed * 2) % 2 === 0 ? " █" : "  ")
                horizontalAlignment: Text.AlignHCenter
                font.family: root.terminalFont; font.pixelSize: 22
                color: root.displayInk
            }
            Text {
                x: 64; y: 978; width: 1792
                text: root.preview ? "MAINFRAME" : "[ ENTER ] authenticate     [ ESC ] clear input"
                horizontalAlignment: Text.AlignHCenter
                font.family: root.terminalFont; font.pixelSize: 16
                color: root.displayInk
                opacity: 0.75
            }
            Rectangle { x: 64; y: 1020; width: 1792; height: 1; color: root.displayAccent; opacity: 0.45 }
        }
    }
}
