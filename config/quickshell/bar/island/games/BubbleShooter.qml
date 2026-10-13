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
    property real aim:-Math.PI/2
    property real lastTime:0
    readonly property string resultText:over?(state.won?"All five skies cleared!":"The bubbles reached the line") : ""
    readonly property var colors:["#fc7a9b","#79dcd7","#a897fc","#ffd579","#79baf2","#a5df83"]
    focus:true
    ArcadeStore {id:store;gameId:"bubbleshooter"}
    function sync():void {score=state.score;over=state.over;scene.requestPaint()}
    function saveGame():void {if(ready)store.save(state)}
    function restart():void {state=Logic.bubbleFresh();ready=true;paused=false;sync();saveGame()}
    function setAim(x:real,y:real):void {aim=Math.max(-2.9,Math.min(-.24,Math.atan2(y-12.25*Math.min(scene.width/12.5,scene.height/13),x-scene.width/2)));scene.requestPaint()}
    function shoot():void {
        if(paused){paused=false;lastTime=Date.now();return}
        const s=Logic.copy(state);if(Logic.bubbleShoot(s,aim)){state=s;sync();saveGame()}
    }
    Component.onCompleted:{const s=store.read();if(Logic.bubbleValid(s)){state=s;ready=true;paused=!s.over;sync()}else restart();lastTime=Date.now()}
    Component.onDestruction:saveGame()
    onPausedChanged:{lastTime=Date.now();scene.requestPaint()}
    Keys.onPressed:event=>{
        if(event.key===Qt.Key_Escape){saveGame();event.accepted=false;return}
        if(event.key===Qt.Key_Left)aim=Math.max(-2.9,aim-.07)
        else if(event.key===Qt.Key_Right)aim=Math.min(-.24,aim+.07)
        else if(event.key===Qt.Key_Space)shoot()
        else if(event.key===Qt.Key_P){paused=!paused;saveGame()}
        else return
        scene.requestPaint();event.accepted=true
    }
    Timer {interval:16;repeat:true;running:root.ready&&!root.paused&&!root.over
        onTriggered:{const now=Date.now(),dt=Math.min(.05,(now-root.lastTime)/1000);root.lastTime=now;if(!root.state.ball)return;const s=Logic.copy(root.state);Logic.bubbleTick(s,dt);root.state=s;root.sync();if(!s.ball||s.over){root.saveGame();if(s.over)root.finished(root.score)}}
    }
    Timer {interval:1000;repeat:true;running:root.ready&&!root.paused&&!root.over;onTriggered:root.saveGame()}
    Rectangle {anchors.fill:parent;radius:18;color:"#12152d";border.color:"#3e426a"}
    Row {x:16;y:10;spacing:9
        Image {source:"bubble-logo.svg";width:34;height:34}
        Column {
            Text {text:"BUBBLE AURORA";color:"#dfd9ff";font.family:Theme.fontFamily;font.bold:true;font.pixelSize:15}
            Text {text:"Sky "+(root.state?root.state.level:1)+" / 5 · "+store.status;color:"#a9b4d8";font.pixelSize:12}
        }
    }
    Rectangle {anchors.right:parent.right;anchors.rightMargin:16;y:13;width:70;height:29;radius:8;color:"#353955"
        Text {anchors.centerIn:parent;text:root.paused?"Resume":"Pause";color:"#ede6ff";font.pixelSize:12}
        MouseArea {anchors.fill:parent;onClicked:{root.paused=!root.paused;root.saveGame();root.forceActiveFocus()}}
    }
    Canvas {
        id:scene
        x:14;y:56;width:parent.width-28;height:parent.height-90
        onWidthChanged:requestPaint()
        onHeightChanged:requestPaint()
        onPaint:{
            const ctx=getContext("2d"),s=root.state
            ctx.clearRect(0,0,width,height)
            const bg=ctx.createLinearGradient(0,0,width,height);bg.addColorStop(0,"#20233f");bg.addColorStop(.5,"#151e39");bg.addColorStop(1,"#252044");ctx.fillStyle=bg;ctx.fillRect(0,0,width,height)
            for(let i=0;i<40;i++){ctx.fillStyle=i%3?"#344264":"#566c89";ctx.beginPath();ctx.arc((i*97+17)%width,(i*61+23)%(height*.8),i%3?1:1.7,0,Math.PI*2);ctx.fill()}
            if(!s)return
            const pitch=Math.min(width/12.5,height/13),yscale=pitch,ox=(width-12.5*pitch)/2,r=pitch*.435,gx=width/2,gy=12.25*pitch
            function ball(x,y,c,size){
                ctx.fillStyle="#080d22";ctx.beginPath();ctx.arc(x+1,y+3,size+1,0,Math.PI*2);ctx.fill()
                const g=ctx.createRadialGradient(x-size*.3,y-size*.4,size*.08,x,y,size);g.addColorStop(0,"#ffffff");g.addColorStop(.22,root.colors[c]);g.addColorStop(1,"#333557")
                ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,size,0,Math.PI*2);ctx.fill();ctx.strokeStyle=root.colors[c];ctx.lineWidth=1.3;ctx.stroke()
                ctx.fillStyle="#ffffff";ctx.globalAlpha=.65;ctx.beginPath();ctx.arc(x-size*.3,y-size*.35,size*.17,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1
                // Color-specific marks keep the board readable beyond hue.
                ctx.strokeStyle="#ffffff";ctx.globalAlpha=.55;ctx.lineWidth=1
                ctx.beginPath();if(c%3===0){ctx.moveTo(x-size*.18,y);ctx.lineTo(x+size*.18,y);ctx.moveTo(x,y-size*.18);ctx.lineTo(x,y+size*.18)}else if(c%3===1){ctx.arc(x,y,size*.2,0,Math.PI*2)}else{ctx.moveTo(x,y-size*.2);ctx.lineTo(x-size*.18,y+size*.15);ctx.lineTo(x+size*.18,y+size*.15);ctx.closePath()}ctx.stroke();ctx.globalAlpha=1
            }
            // Danger line.
            ctx.strokeStyle="#cd7386";ctx.globalAlpha=.5;ctx.lineWidth=1
            for(let x=0;x<width;x+=12){ctx.beginPath();ctx.moveTo(x,9.26*yscale);ctx.lineTo(x+5,9.26*yscale);ctx.stroke()}ctx.globalAlpha=1
            for(let i=0;i<144;i++)if(s.grid[i]>=0){const p=Logic.bubblePos(i);ball(ox+p.x*pitch,p.y*yscale,s.grid[i],r)}
            if(!s.ball&&!s.over){
                let bx=6.25,by=12.25,vx=Math.cos(root.aim),vy=Math.sin(root.aim)
                ctx.fillStyle=root.colors[s.current];ctx.globalAlpha=.4
                for(let k=0;k<36;k++){
                    bx+=vx*.28;by+=vy*.28;if(bx<.45){bx=.45;vx=Math.abs(vx)}if(bx>12.05){bx=12.05;vx=-Math.abs(vx)}
                    if(by<.6||s.grid.some((c,i)=>c>=0&&Math.hypot(Logic.bubblePos(i).x-bx,Logic.bubblePos(i).y-by)<.9))break
                    ctx.beginPath();ctx.arc(ox+bx*pitch,by*yscale,2,0,Math.PI*2);ctx.fill()
                }ctx.globalAlpha=1
            }
            ctx.save();ctx.translate(gx,gy);ctx.rotate(root.aim+Math.PI/2)
            ctx.fillStyle="#677da2";ctx.fillRect(-9,-r*1.8,18,r*1.8);ctx.fillStyle="#b8c6e4";ctx.fillRect(-5,-r*1.8,10,8);ctx.restore()
            ball(gx,gy,s.current,r);ball(gx+pitch*1.8,gy,s.next,r*.67)
            if(s.ball)ball(ox+s.ball.x*pitch,s.ball.y*yscale,s.ball.color,r)
            if(root.paused){ctx.fillStyle="rgba(16,21,43,0.78)";ctx.fillRect(0,0,width,height);ctx.fillStyle="#e7e0ff";ctx.font="bold 22px sans-serif";ctx.textAlign="center";ctx.fillText("PAUSED",width/2,height/2);ctx.font="13px sans-serif";ctx.fillText("Click / Space to resume",width/2,height/2+27)}
        }
        MouseArea {anchors.fill:parent;hoverEnabled:true;onPositionChanged:mouse=>root.setAim(mouse.x,mouse.y);onClicked:mouse=>{root.setAim(mouse.x,mouse.y);root.shoot();root.forceActiveFocus()}}
    }
    Text {anchors.bottom:parent.bottom;anchors.bottomMargin:7;anchors.horizontalCenter:parent.horizontalCenter;text:"Match 3+ · Wall shots work · New row every 6 shots · Space shoot · P pause";color:"#95a7ce";font.pixelSize:10}
}
