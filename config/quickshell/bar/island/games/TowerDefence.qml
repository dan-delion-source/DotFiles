import QtQuick
import "../../../theme"
import "ArcadeLogic.js" as Logic

FocusScope {
    id:root
    property int score:0
    property bool over:false
    property color tint:Theme.accent
    signal finished(int score)
    property var state:null
    property bool ready:false
    property bool paused:false
    property int selected:-1
    property int kind:0
    property real lastTime:0
    property string message:"Select a build pad, choose a tower, then Build."
    readonly property string resultText:over?(state.won?"The citadel stands!":"The citadel fell") : ""
    readonly property var chosen:state?state.towers.find(t=>t.pad===selected):null
    readonly property var colors:["#ffc977","#7ce0ef","#f89b92"]
    focus:true
    ArcadeStore {id:store;gameId:"towerdefence"}
    function sync():void{score=state.score;over=state.over;map.requestPaint()}
    function saveGame():void{if(ready)store.save(state)}
    function restart():void{state=Logic.towerFresh();ready=true;paused=false;selected=-1;message="Build towers before sending the first wave.";sync();saveGame()}
    function act(action:string):void{
        const s=Logic.copy(state)
        let success=false
        if(action==="build")success=Logic.towerBuild(s,selected,kind)
        else if(action==="upgrade")success=Logic.towerUpgrade(s,selected)
        else if(action==="sell")success=Logic.towerSell(s,selected)
        else if(action==="wave")success=Logic.towerWave(s)
        if(success){state=s;message=action==="wave"?"Wave incoming. Hold the winding road!":"Citadel defenses updated.";sync();saveGame()}
        else message=action==="wave"?"Finish the current wave first.":"Select a pad and check your gold / upgrade level."
        forceActiveFocus()
    }
    Component.onCompleted:{const s=store.read();if(Logic.towerValid(s)){state=s;ready=true;paused=s.active;sync()}else restart();lastTime=Date.now()}
    Component.onDestruction:saveGame()
    onPausedChanged:{lastTime=Date.now();map.requestPaint()}
    onSelectedChanged:map.requestPaint()
    onKindChanged:map.requestPaint()
    Keys.onPressed:event=>{
        if(event.key===Qt.Key_Escape){saveGame();event.accepted=false;return}
        if(event.key===Qt.Key_Space){if(state.active)paused=!paused;else act("wave")}
        else if(event.key===Qt.Key_1)kind=0
        else if(event.key===Qt.Key_2)kind=1
        else if(event.key===Qt.Key_3)kind=2
        else if(event.key===Qt.Key_U)act("upgrade")
        else return
        saveGame();event.accepted=true
    }
    Timer {interval:16;repeat:true;running:root.ready&&root.state.active&&!root.paused&&!root.over
        onTriggered:{const now=Date.now(),dt=Math.min(.05,(now-root.lastTime)/1000);root.lastTime=now;const s=Logic.copy(root.state);Logic.towerTick(s,dt);root.state=s;root.sync();if(!s.active||s.over){root.saveGame();if(s.over)root.finished(root.score)}}
    }
    Timer {interval:1000;repeat:true;running:root.ready&&root.state.active&&!root.paused&&!root.over;onTriggered:root.saveGame()}
    Rectangle {anchors.fill:parent;radius:18;color:"#14272a";border.color:"#416164"}
    Row {x:16;y:10;spacing:10
        Image {source:"tower-logo.svg";width:36;height:36}
        Column {
            Text {text:"CITADEL GROVE";color:"#e8d8af";font.family:Theme.fontFamily;font.pixelSize:15;font.bold:true}
            Text {text:"Wave "+(root.state?root.state.wave:0)+" / 10 · Gold "+(root.state?root.state.cash:0)+" · Lives "+(root.state?root.state.lives:15);color:"#b1cdbe";font.pixelSize:12}
        }
    }
    Row {anchors.right:parent.right;anchors.rightMargin:16;y:14;spacing:6
        Rectangle {width:64;height:29;radius:8;color:"#345451"
            Text {anchors.centerIn:parent;text:root.paused?"Resume":"Pause";color:"#e7f3dc";font.pixelSize:11}
            MouseArea {anchors.fill:parent;onClicked:{root.paused=!root.paused;root.saveGame();root.forceActiveFocus()}}
        }
        Rectangle {width:91;height:29;radius:8;color:root.state&&root.state.active?"#3c5149":"#856b3d"
            Text {anchors.centerIn:parent;text:root.state&&root.state.active?"Wave active":"Next wave";color:"#fff2ca";font.pixelSize:11}
            MouseArea {anchors.fill:parent;onClicked:root.act("wave")}
        }
    }
    Canvas {
        id:map
        x:14;y:58;width:parent.width-28;height:parent.height-174
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            const ctx=getContext("2d"),s=root.state
            ctx.clearRect(0,0,width,height)
            const bg=ctx.createLinearGradient(0,0,width,height);bg.addColorStop(0,"#224c46");bg.addColorStop(1,"#17383e");ctx.fillStyle=bg;ctx.fillRect(0,0,width,height)
            // Groves, rock gardens and small glints: deterministic decoration.
            for(let i=0;i<48;i++){
                const x=((i*113+33)%997)/997*width,y=((i*179+91)%991)/991*height
                ctx.fillStyle=i%3?"#2c5950":"#326259";ctx.beginPath();ctx.arc(x,y,7+i%5,0,Math.PI*2);ctx.fill()
                ctx.fillStyle="#47705e";ctx.beginPath();ctx.arc(x-2,y-3,4+i%3,0,Math.PI*2);ctx.fill()
            }
            function road(stroke,w){ctx.beginPath();Logic.path.forEach((p,i)=>{if(i)ctx.lineTo(p.x*width,p.y*height);else ctx.moveTo(p.x*width,p.y*height)});ctx.strokeStyle=stroke;ctx.lineWidth=w;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke()}
            road("#102c2e",36);road("#796f56",29);road("#ad9b73",23)
            ctx.strokeStyle="#c8b78b";ctx.lineWidth=1;for(let i=0;i<80;i++){const p=Logic.pointAt(i/80);ctx.beginPath();ctx.arc(p.x*width,p.y*height,1,0,Math.PI*2);ctx.stroke()}
            // Exit citadel.
            const ex=width-20,ey=.78*height
            ctx.fillStyle="#8d9c9e";ctx.fillRect(ex-8,ey-20,28,40);ctx.fillStyle="#bbc3af";ctx.fillRect(ex-12,ey-26,10,15);ctx.fillRect(ex+10,ey-26,10,15);ctx.fillStyle="#213c3d";ctx.fillRect(ex+2,ey-2,9,21)
            if(!s)return
            if(root.selected>=0){const p=Logic.pads[root.selected],tower=root.chosen,spec=Logic.towerKinds[tower?tower.kind:root.kind],range=spec.range+(tower?(tower.level-1)*.018:0);ctx.save();ctx.translate(p.x*width,p.y*height);ctx.scale(width,height);ctx.fillStyle="rgba(123,221,202,0.09)";ctx.beginPath();ctx.arc(0,0,range,0,Math.PI*2);ctx.fill();ctx.restore();ctx.strokeStyle="#689f8c";ctx.lineWidth=1;ctx.stroke()}
            Logic.pads.forEach((p,i)=>{
                const x=p.x*width,y=p.y*height,t=s.towers.find(t=>t.pad===i)
                ctx.fillStyle="#173432";ctx.beginPath();ctx.arc(x+1,y+3,18,0,Math.PI*2);ctx.fill();ctx.fillStyle=t?"#637b75":"#3d6860";ctx.beginPath();ctx.arc(x,y,17,0,Math.PI*2);ctx.fill();ctx.strokeStyle=i===root.selected?"#ffe0a0":"#80a48a";ctx.lineWidth=i===root.selected?3:1.3;ctx.stroke()
                if(!t){ctx.strokeStyle="#9ab5a4";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x-5,y);ctx.lineTo(x+5,y);ctx.moveTo(x,y-5);ctx.lineTo(x,y+5);ctx.stroke();return}
                ctx.fillStyle=root.colors[t.kind];ctx.strokeStyle="#263e40";ctx.lineWidth=2
                if(t.kind===0){ctx.beginPath();ctx.moveTo(x,y-13);ctx.lineTo(x+9,y+8);ctx.lineTo(x-9,y+8);ctx.closePath();ctx.fill();ctx.stroke()}
                else if(t.kind===1){ctx.beginPath();ctx.moveTo(x,y-13);ctx.lineTo(x+10,y);ctx.lineTo(x,y+13);ctx.lineTo(x-10,y);ctx.closePath();ctx.fill();ctx.stroke()}
                else {ctx.fillRect(x-10,y-8,20,17);ctx.fillStyle="#5f4751";ctx.beginPath();ctx.arc(x,y-7,7,0,Math.PI*2);ctx.fill()}
                for(let star=0;star<t.level;star++){ctx.fillStyle="#fff0ba";ctx.beginPath();ctx.arc(x-6+star*6,y+21,2,0,Math.PI*2);ctx.fill()}
            })
            s.enemies.forEach(e=>{
                const p=Logic.pointAt(e.progress),x=p.x*width,y=p.y*height,r=e.boss?13:8
                ctx.fillStyle=e.slow>0?"#88dbe4":e.boss?"#d28284":"#b29fdd";ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.strokeStyle="#46334d";ctx.lineWidth=2;ctx.stroke()
                ctx.fillStyle="#251b3a";ctx.beginPath();ctx.arc(x-3,y-1,1.6,0,Math.PI*2);ctx.arc(x+3,y-1,1.6,0,Math.PI*2);ctx.fill()
                ctx.fillStyle="#162c32";ctx.fillRect(x-12,y-r-7,24,3);ctx.fillStyle="#b7edac";ctx.fillRect(x-12,y-r-7,24*Math.max(0,e.hp/e.maxHp),3)
            })
            s.shots.forEach(p=>{ctx.strokeStyle=root.colors[p.kind];ctx.globalAlpha=p.life/.16;ctx.lineWidth=p.kind===2?4:2;ctx.beginPath();ctx.moveTo(p.x*width,p.y*height);ctx.lineTo(p.tx*width,p.ty*height);ctx.stroke();ctx.globalAlpha=1})
            if(root.paused&&s.active){ctx.fillStyle="rgba(17,44,47,0.7)";ctx.fillRect(0,0,width,height);ctx.fillStyle="#f4e9c6";ctx.textAlign="center";ctx.font="bold 22px sans-serif";ctx.fillText("DEFENSE PAUSED",width/2,height/2);ctx.font="13px sans-serif";ctx.fillText("Resume when you are ready",width/2,height/2+25)}
        }
        MouseArea {anchors.fill:parent;onClicked:mouse=>{let best=-1,dist=28;Logic.pads.forEach((p,i)=>{const d=Math.hypot(p.x*map.width-mouse.x,p.y*map.height-mouse.y);if(d<dist){best=i;dist=d}});root.selected=best;root.forceActiveFocus()}}
    }
    Row {x:14;y:parent.height-107;spacing:7
        Repeater {model:3
            Rectangle {required property int index;width:105;height:33;radius:8;color:root.kind===index?"#526952":"#2a4547";border.color:root.colors[index];border.width:root.kind===index?2:0
                Text {anchors.centerIn:parent;text:Logic.towerKinds[parent.index].name+" · "+Logic.towerKinds[parent.index].cost;color:"#f3e9d5";font.pixelSize:11}
                MouseArea {anchors.fill:parent;onClicked:{root.kind=parent.index;root.forceActiveFocus()}}
            }
        }
        Repeater {model:["build","upgrade","sell"]
            Rectangle {required property string modelData;width:82;height:33;radius:8;color:modelData==="sell"?"#5b4644":"#536746"
                Text {anchors.centerIn:parent;text:parent.modelData==="upgrade"&&root.chosen?"Up · "+Math.floor(Logic.towerKinds[root.chosen.kind].cost*.75*root.chosen.level):parent.modelData.charAt(0).toUpperCase()+parent.modelData.slice(1);color:"#fff0d1";font.pixelSize:11}
                MouseArea {anchors.fill:parent;onClicked:root.act(parent.modelData)}
            }
        }
    }
    Text {x:16;y:parent.height-65;width:parent.width-32;elide:Text.ElideRight;text:root.message;color:"#c6d8bd";font.pixelSize:12}
    Text {x:16;y:parent.height-43;text:"Arrow: rapid · Frost: slows · Cannon: splash · Upgrade to level 3";color:"#99b6aa";font.pixelSize:11}
    Text {anchors.bottom:parent.bottom;anchors.bottomMargin:7;anchors.horizontalCenter:parent.horizontalCenter;text:"Space wave / pause · 1–3 tower type · U upgrade · Esc save · R restart · "+store.status;color:"#81a398";font.pixelSize:10}
}
