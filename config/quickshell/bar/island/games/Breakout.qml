import QtQuick
import "../../../theme"
import "BreakoutLogic.js" as Game

FocusScope {
    id: root
    property int score: 0
    property bool over: false
    property color tint: Theme.accent
    signal finished(int score)

    property var session: null
    property bool ready: false
    property bool paused: false
    property bool leftHeld: false
    property bool rightHeld: false
    property bool mouseMode: false
    property real mouseX: 360
    property real lastTime: 0
    property int revision: 0
    property bool finishSent: false
    readonly property string resultText: session && session.phase === "won"
        ? "ALL 15 SECTORS CLEARED!" : "END OF TRANSMISSION"
    readonly property string terminalFont: "monospace"
    focus: true

    BreakoutStore { id: store }

    function sync(): void {
        // The simulation mutates a JS object in place. Notify QML so phase,
        // overlay and timer bindings update even when the score is unchanged.
        sessionChanged()
        score = session.score
        over = session.phase === "won" || session.phase === "lost"
        revision++
        screen.requestPaint()
        if (over && !finishSent) {
            finishSent = true
            finished(score)
        }
    }
    function saveGame(): void {
        if (ready && session) store.save(Game.snapshot(session))
    }
    function restart(): void {
        session = Game.fresh()
        ready = true
        paused = false
        finishSent = false
        leftHeld = false
        rightHeld = false
        mouseMode = false
        lastTime = Date.now()
        sync()
        saveGame()
    }
    function action(): void {
        if (!ready || over) return
        if (paused) paused = false
        else if (session.phase === "serve" || session.phase === "clear") Game.launch(session)
        else paused = true
        lastTime = Date.now()
        forceActiveFocus()
        sync()
        saveGame()
    }
    function pauseGame(): void {
        if (!ready || over) return
        paused = !paused
        lastTime = Date.now()
        leftHeld = false
        rightHeld = false
        sync()
        saveGame()
        forceActiveFocus()
    }
    Component.onCompleted: {
        const saved = store.read()
        if (Game.valid(saved)) {
            session = saved
            ready = true
            paused = saved.phase === "play"
            finishSent = saved.phase === "won" || saved.phase === "lost"
            sync()
        } else restart()
        lastTime = Date.now()
    }
    Component.onDestruction: saveGame()
    onActiveFocusChanged: {
        if (!activeFocus) {
            leftHeld = false
            rightHeld = false
            if (ready && session.phase === "play") {
                paused = true
                saveGame()
                screen.requestPaint()
            }
        }
    }
    Keys.onPressed: event => {
        if (event.key === Qt.Key_Escape) {
            paused = true
            saveGame()
            event.accepted = false
            return
        }
        if (event.key === Qt.Key_Left || event.key === Qt.Key_A) {
            leftHeld = true
            mouseMode = false
        } else if (event.key === Qt.Key_Right || event.key === Qt.Key_D) {
            rightHeld = true
            mouseMode = false
        } else if (event.key === Qt.Key_P) {
            if (!event.isAutoRepeat) pauseGame()
        } else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (over) { event.accepted = false; return }
            if (!event.isAutoRepeat) action()
        } else return // R belongs to GamesPanel's restart action.
        event.accepted = true
    }
    Keys.onReleased: event => {
        if (event.isAutoRepeat) return
        if (event.key === Qt.Key_Left || event.key === Qt.Key_A) leftHeld = false
        else if (event.key === Qt.Key_Right || event.key === Qt.Key_D) rightHeld = false
        else return
        event.accepted = true
    }
    Timer {
        interval: 16
        repeat: true
        running: root.ready && !root.paused && !root.over
        onTriggered: {
            const now = Date.now()
            const dt = Math.max(0, Math.min(.05, (now - root.lastTime) / 1000))
            root.lastTime = now
            const before = root.session.phase
            Game.tick(root.session, dt, root.mouseMode ? {x: root.mouseX} : {direction: Number(root.rightHeld) - Number(root.leftHeld)})
            root.sync()
            if (before !== root.session.phase) root.saveGame()
        }
    }
    Timer {
        interval: 2000
        repeat: true
        running: root.ready && !root.paused && !root.over && root.session.phase === "play"
        onTriggered: root.saveGame()
    }

    Rectangle {
        anchors.fill: parent
        radius: 18
        color: "#080d1b"
        border.color: "#27354e"
        border.width: 2
    }
    Row {
        x: 18; y: 12; spacing: 10
        Image { source: "breakout-logo.svg"; width: 40; height: 40; sourceSize.width: 96; sourceSize.height: 96 }
        Column {
            spacing: 2
            Text { text: "NEON BREAKOUT"; font.family: root.terminalFont; font.pixelSize: 18; font.bold: true; font.letterSpacing: 2; color: "#b7f8ff" }
            Text {
                text: { root.revision; return root.session ? "SECTOR " + String(root.session.level).padStart(2,"0") + " / 15  //  " + Game.LEVELS[root.session.level - 1].name : "BOOTING" }
                font.family: root.terminalFont; font.pixelSize: 10; color: "#8095b8"
            }
        }
    }
    Row {
        anchors.right: parent.right; anchors.rightMargin: 18; y: 14; spacing: 14
        Column {
            Text { text: "SCORE"; color: "#778dab"; font.family: root.terminalFont; font.pixelSize: 9; font.letterSpacing: 2 }
            Text { text: String(root.score).padStart(7,"0"); color: "#ffe6a0"; font.family: root.terminalFont; font.pixelSize: 19; font.bold: true }
        }
        Rectangle {
            width: 62; height: 30; radius: 5; color: "#16243b"; border.color: "#304b68"
            Text { anchors.centerIn: parent; text: root.paused ? "RESUME" : "PAUSE"; font.family: root.terminalFont; font.pixelSize: 10; color: "#b9d6ed" }
            MouseArea { anchors.fill: parent; onClicked: root.pauseGame() }
        }
    }
    Item {
        id: viewport
        x: 18; y: 65; width: parent.width - 36; height: parent.height - 148
        readonly property real factor: Math.min(width / Game.W, height / Game.H)
        Rectangle {
            anchors.centerIn: parent
            width: Game.W * viewport.factor + 4; height: Game.H * viewport.factor + 4
            color: "#081324"; border.width: 2; border.color: "#315368"; radius: 3
        }
        Canvas {
            id: screen
            anchors.centerIn: parent
            width: Game.W * viewport.factor; height: Game.H * viewport.factor
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d"), s = root.session
                ctx.reset()
                ctx.scale(width / Game.W, height / Game.H)
                ctx.fillStyle = "#060b19"; ctx.fillRect(0,0,Game.W,Game.H)
                const backdrop = ctx.createLinearGradient(0,0,0,Game.H)
                backdrop.addColorStop(0,"#111229"); backdrop.addColorStop(.6,"#0b1429"); backdrop.addColorStop(1,"#0c1d2a")
                ctx.fillStyle = backdrop; ctx.fillRect(0,0,Game.W,Game.H)
                // A quiet starfield, perspective grid and CRT scanlines.
                for (let i=0;i<47;i++) {
                    ctx.fillStyle = i%4 ? "#233253" : "#58708b"
                    ctx.fillRect((i*137+19)%Game.W,(i*79+17)%Game.H,i%4?1:2,1)
                }
                ctx.strokeStyle = "#18334b"; ctx.lineWidth = 1
                for (let x=-500;x<1300;x+=90) {ctx.beginPath();ctx.moveTo(Game.W/2,270);ctx.lineTo(x,Game.H);ctx.stroke()}
                for (let y=280;y<Game.H;y+=Math.max(10,(y-260)*.19)) {ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(Game.W,y);ctx.stroke()}
                if (!s) return
                ctx.save()
                if(s.shake>0)ctx.translate(Math.sin(s.elapsed*110)*s.shake*18,Math.cos(s.elapsed*95)*s.shake*13)
                ctx.fillStyle = "#192b45";ctx.fillRect(0,0,4,Game.H);ctx.fillRect(Game.W-4,0,4,Game.H);ctx.fillRect(0,0,Game.W,4)
                ctx.fillStyle = "#5ca6bb";ctx.fillRect(4,4,1,Game.H);ctx.fillRect(Game.W-5,4,1,Game.H)
                // Bricks use bevels and armour strips rather than flat blocks.
                s.bricks.forEach(brick => {
                    if (!brick.hp) return
                    const steel=brick.hp<0, color=steel?"#60728d":Game.COLORS[brick.color]
                    ctx.fillStyle="#020812";ctx.fillRect(brick.x+2,brick.y+4,brick.w,brick.h)
                    ctx.globalAlpha=.12;ctx.fillStyle=color;ctx.fillRect(brick.x-3,brick.y-3,brick.w+6,brick.h+6);ctx.globalAlpha=1
                    ctx.fillStyle=steel?"#334155":color;ctx.fillRect(brick.x,brick.y,brick.w,brick.h)
                    ctx.fillStyle=steel?"#a3adbd":"#ffffff";ctx.globalAlpha=.45;ctx.fillRect(brick.x+1,brick.y+1,brick.w-2,2);ctx.globalAlpha=1
                    ctx.fillStyle="#081020";ctx.globalAlpha=.28;ctx.fillRect(brick.x+1,brick.y+brick.h-4,brick.w-2,3);ctx.globalAlpha=1
                    if(steel){ctx.fillStyle="#17283d";ctx.fillRect(brick.x+6,brick.y+6,3,4);ctx.fillRect(brick.x+brick.w-9,brick.y+6,3,4)}
                    else if(brick.hp>1){for(let n=0;n<brick.hp;n++){ctx.fillStyle="#fff3cf";ctx.fillRect(brick.x+brick.w/2+(n-(brick.hp-1)/2)*6-1.5,brick.y+7,3,3)}}
                    if(!steel&&brick.hp<brick.max){ctx.strokeStyle="#18304b";ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(brick.x+brick.w*.6,brick.y);ctx.lineTo(brick.x+brick.w*.4,brick.y+8);ctx.lineTo(brick.x+brick.w*.6,brick.y+brick.h);ctx.stroke()}
                })
                if (s.shield>0) {
                    ctx.fillStyle="#5cebbd";ctx.globalAlpha=.12;ctx.fillRect(4,Game.H-19,Game.W-8,12);ctx.globalAlpha=.85
                    for(let x=8;x<Game.W-8;x+=12)ctx.fillRect(x,Game.H-13,8,2)
                    ctx.globalAlpha=1
                }
                function paddle(cx,cy,w,color,echo) {
                    ctx.fillStyle=color;ctx.globalAlpha=echo?.1:.16;ctx.fillRect(cx-w/2-4,cy-4,w+8,18);ctx.globalAlpha=1
                    ctx.fillStyle=echo?"#352e64":"#135572";ctx.fillRect(cx-w/2,cy,w,10)
                    ctx.fillStyle=color;ctx.fillRect(cx-w/2,cy,w,3);ctx.fillRect(cx-w/2,cy,7,10);ctx.fillRect(cx+w/2-7,cy,7,10)
                    ctx.fillStyle="#efffff";ctx.globalAlpha=.7;ctx.fillRect(cx-w*.2,cy+1,w*.4,1);ctx.globalAlpha=1
                    if(!echo&&s.effects.laser>0){ctx.fillStyle="#ff5e93";ctx.fillRect(cx-w/2+3,cy-7,6,13);ctx.fillRect(cx+w/2-9,cy-7,6,13)}
                }
                if(s.effects.echo>0)paddle(Game.W-s.paddle,Game.ECHO_Y,Game.paddleWidth(s)*.66,"#ac94ff",true)
                paddle(s.paddle,Game.PADDLE_Y,Game.paddleWidth(s),"#50dfff",false)
                s.lasers.forEach(laser => {ctx.fillStyle="#ff5e93";ctx.globalAlpha=.17;ctx.fillRect(laser.x-5,laser.y,10,17);ctx.globalAlpha=1;ctx.fillStyle="#ffd8ed";ctx.fillRect(laser.x-1.5,laser.y,3,13)})
                s.balls.forEach(ball => {
                    ball.trail.forEach((p,i)=>{ctx.fillStyle="#69ecff";ctx.globalAlpha=(i+1)/ball.trail.length*.2;const r=Game.R*(i+1)/ball.trail.length;ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fill()});ctx.globalAlpha=1
                    ctx.fillStyle="#52dfff";ctx.globalAlpha=.12;ctx.beginPath();ctx.arc(ball.x,ball.y,12,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1
                    ctx.fillStyle="#84f3ff";ctx.beginPath();ctx.arc(ball.x,ball.y,Game.R,0,Math.PI*2);ctx.fill();ctx.fillStyle="#ffffff";ctx.fillRect(ball.x-2,ball.y-3,3,2)
                })
                const powerGlyphs={multi:"M",wide:"W",echo:"E",shield:"N",slow:"S",laser:"L",life:"+"}
                s.drops.forEach(drop => {
                    ctx.fillStyle="#081222";ctx.fillRect(drop.x-13,drop.y-10,26,20);ctx.strokeStyle=Game.POWER_COLORS[drop.kind];ctx.lineWidth=2;ctx.strokeRect(drop.x-13,drop.y-10,26,20)
                    ctx.fillStyle=Game.POWER_COLORS[drop.kind];ctx.font="bold 13px monospace";ctx.textAlign="center";ctx.fillText(powerGlyphs[drop.kind],drop.x,drop.y+5)
                })
                s.particles.forEach(p=>{ctx.fillStyle=p.color;ctx.globalAlpha=Math.max(0,p.life/.6);ctx.fillRect(p.x-1.5,p.y-1.5,3,3)});ctx.globalAlpha=1
                ctx.font="bold 10px monospace";ctx.textAlign="left";ctx.fillStyle="#738aa7";ctx.fillText("BRICKS "+String(Game.left(s)).padStart(2,"0"),16,24)
                ctx.textAlign="right";ctx.fillStyle="#ff9fb8";ctx.fillText("LIVES "+s.lives+"   BALLS "+s.balls.length,Game.W-16,24)
                if(s.combo>1){ctx.fillStyle="#ffe78a";ctx.font="bold 14px monospace";ctx.textAlign="left";ctx.fillText("COMBO x"+s.combo,16,Game.H-39)}
                if(s.noticeClock>0&&s.phase==="play"){ctx.globalAlpha=Math.min(1,s.noticeClock);ctx.textAlign="center";ctx.font="bold 12px monospace";ctx.fillStyle="#ffe9ba";ctx.fillText(s.notice,Game.W/2,Game.H-64);ctx.globalAlpha=1}
                ctx.restore()
                if(s.flash>0){ctx.globalAlpha=s.flash*.55;ctx.fillStyle="#d9faff";ctx.fillRect(0,0,Game.W,Game.H);ctx.globalAlpha=1}
                // Screen-door texture; the QML overlay remains crisp above it.
                ctx.fillStyle="rgba(0,0,0,0.12)";for(let y=0;y<Game.H;y+=4)ctx.fillRect(0,y,Game.W,1)
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                onPositionChanged: mouse => {
                    root.mouseX = mouse.x / screen.width * Game.W
                    root.mouseMode = true
                    if (root.ready && root.session.phase === "serve" && !root.paused) {Game.movePaddle(root.session,root.mouseX);root.sync()}
                }
                onClicked: {
                    root.forceActiveFocus()
                    if (root.paused || root.session.phase === "serve" || root.session.phase === "clear") root.action()
                }
            }
        }
        Rectangle {
            anchors.centerIn: parent
            width: Math.min(420,parent.width-32); height: 150
            color: "#ed091324"; border.color: "#3e8396"; border.width: 1; radius: 8
            visible: root.ready && !root.over && (root.paused || root.session.phase !== "play")
            Column {
                anchors.centerIn: parent; spacing: 10
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: {root.revision;return root.paused?"GAME PAUSED":root.session&&root.session.phase==="clear"?"SECTOR CLEAR":"READY PLAYER ONE"}
                    color: "#8ef1ff"; font.family: root.terminalFont; font.pixelSize: 22; font.bold: true; font.letterSpacing: 1
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: {root.revision;return root.session&&root.session.phase==="clear"?"NEXT: "+Game.LEVELS[root.session.level].name:"MOUSE / ARROWS / A–D TO MOVE"}
                    color: "#b0bfd7"; font.family: root.terminalFont; font.pixelSize: 11
                }
                Text {anchors.horizontalCenter: parent.horizontalCenter;text: "[ SPACE OR CLICK TO CONTINUE ]";color: "#ffe09a";font.family: root.terminalFont;font.pixelSize: 11}
            }
            MouseArea {anchors.fill: parent;onClicked: root.action()}
        }
    }
    // All seven drops are explained in-place without relying on an icon font.
    Row {
        y: parent.height - 70; anchors.horizontalCenter: parent.horizontalCenter; spacing: 8
        Repeater {
            model: [{k:"multi",g:"M",label:"MULTI"},{k:"wide",g:"W",label:"WIDE"},{k:"echo",g:"E",label:"ECHO"},{k:"shield",g:"N",label:"NET"},{k:"slow",g:"S",label:"SLOW"},{k:"laser",g:"L",label:"LASER"},{k:"life",g:"+",label:"LIFE"}]
            Column {
                id: badge
                required property var modelData
                readonly property string counter: {
                    root.revision
                    if(!root.session)return ""
                    if(modelData.k==="shield")return root.session.shield?String(root.session.shield):""
                    const seconds=root.session.effects[modelData.k]||0
                    return seconds>0?Math.ceil(seconds)+"s":""
                }
                spacing: 3; width: 79
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter; width: 30; height: 20; radius: 3
                    color: "#111f32"; border.color: Game.POWER_COLORS[badge.modelData.k]; border.width: 1
                    Text {anchors.centerIn: parent;text: badge.modelData.g;color: Game.POWER_COLORS[badge.modelData.k];font.family: root.terminalFont;font.bold: true;font.pixelSize: 11}
                }
                Text {anchors.horizontalCenter: parent.horizontalCenter;text:badge.modelData.label+(badge.counter?" "+badge.counter:"");color:badge.counter?Game.POWER_COLORS[badge.modelData.k]:"#778ca9";font.family:root.terminalFont;font.pixelSize:9}
            }
        }
    }
    Text {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 9; anchors.horizontalCenter: parent.horizontalCenter
        text: "SPACE launch / pause   P pause   R restart   ESC save & exit   //   " + store.status
        color: "#6d86a5"; font.family: root.terminalFont; font.pixelSize: 9
    }
}
