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
    property bool preview:false
    readonly property string resultText:over?"Landscape restored!":""
    readonly property int n:state?state.n:4
    readonly property real side:Math.min(width-48,height-116)
    readonly property real tile:side/n
    focus:true
    ArcadeStore {id:store;gameId:"slidingpuzzle"}
    function sync():void {over=state.over;score=Math.max(1,2500-state.moves*8-Math.floor(state.seconds/2))}
    function saveGame():void {if(ready)store.save(state)}
    function newSize(size:int):void {state=Logic.puzzleFresh(size);ready=true;preview=false;sync();saveGame()}
    function restart():void {newSize(state?state.n:4)}
    function move(value:int):void {
        if(preview)return
        const next=Logic.copy(state)
        if(!Logic.puzzleMove(next,next.tiles.indexOf(value)))return
        state=next;sync();saveGame();if(over)finished(score)
    }
    Component.onCompleted:{const s=store.read();if(Logic.puzzleValid(s)){state=s;ready=true;sync()}else restart()}
    Component.onDestruction:saveGame()
    Timer {interval:1000;repeat:true;running:root.ready&&!root.over&&!root.preview;onTriggered:{const s=Logic.copy(root.state);s.seconds++;root.state=s;root.sync();if(s.seconds%5===0)root.saveGame()}}
    Keys.onPressed:event=>{
        if(event.key===Qt.Key_Escape){saveGame();event.accepted=false;return}
        if(event.key===Qt.Key_Space){preview=!preview;event.accepted=true;return}
        const blank=state.tiles.indexOf(0),r=Math.floor(blank/n),c=blank%n
        let from=-1
        if(event.key===Qt.Key_Left&&c<n-1)from=blank+1
        if(event.key===Qt.Key_Right&&c>0)from=blank-1
        if(event.key===Qt.Key_Up&&r<n-1)from=blank+n
        if(event.key===Qt.Key_Down&&r>0)from=blank-n
        if(from>=0){move(state.tiles[from]);event.accepted=true}
    }
    Rectangle {anchors.fill:parent;radius:18;color:"#122735";border.color:"#395469"}
    Row {x:18;y:12;spacing:10
        Image {source:"puzzle-logo.svg";width:34;height:34}
        Column {
            Text {text:"SLIDING HORIZONS";color:"#d0edec";font.bold:true;font.pixelSize:15;font.family:Theme.fontFamily}
            Text {text:(root.state?root.state.moves:0)+" moves · "+(root.state?root.state.seconds:0)+"s · "+store.status;color:"#a9c5d5";font.pixelSize:12}
        }
    }
    Row {anchors.right:parent.right;anchors.rightMargin:18;y:14;spacing:6
        Repeater {model:[3,4,5]
            Rectangle {required property int modelData;width:40;height:28;radius:8;color:root.n===modelData?"#3b8588":"#294657"
                Text {anchors.centerIn:parent;text:parent.modelData+"×"+parent.modelData;color:"#e9faf5";font.pixelSize:11}
                MouseArea {anchors.fill:parent;onClicked:{root.newSize(parent.modelData);root.forceActiveFocus()}}
            }
        }
        Rectangle {width:65;height:28;radius:8;color:root.preview?"#3b8588":"#294657"
            Text {anchors.centerIn:parent;text:"Preview";color:"#e9faf5";font.pixelSize:11}
            MouseArea {anchors.fill:parent;onClicked:root.preview=!root.preview}
        }
    }
    Rectangle {
        id:board
        width:root.side;height:width;y:68;anchors.horizontalCenter:parent.horizontalCenter
        color:"#091922";radius:12
        Repeater {
            model:root.n*root.n-1
            Rectangle {
                id:piece
                required property int index
                readonly property int value:index+1
                readonly property int slot:root.state?root.state.tiles.indexOf(value):index
                x:(slot%root.n)*root.tile+2;y:Math.floor(slot/root.n)*root.tile+2
                width:root.tile-4;height:width;radius:6;clip:true
                color:"#38657c"
                Behavior on x {NumberAnimation {duration:140;easing.type:Easing.OutCubic}}
                Behavior on y {NumberAnimation {duration:140;easing.type:Easing.OutCubic}}
                Image {width:root.side;height:root.side;source:"puzzle-art.svg";x:-((piece.value-1)%root.n)*root.tile-2;y:-Math.floor((piece.value-1)/root.n)*root.tile-2;sourceSize.width:800;sourceSize.height:800}
                Rectangle {anchors.left:parent.left;anchors.top:parent.top;anchors.margins:5;width:25;height:23;radius:6;color:"#b5142936"
                    Text {anchors.centerIn:parent;text:piece.value;color:"#fff5dd";font.bold:true;font.pixelSize:12}
                }
                Rectangle {anchors.fill:parent;radius:6;color:"transparent";border.color:"#88b8c4";border.width:1;opacity:.7}
                MouseArea {anchors.fill:parent;onClicked:{root.move(piece.value);root.forceActiveFocus()}}
            }
        }
        Image {anchors.fill:parent;source:"puzzle-art.svg";visible:root.preview;sourceSize.width:800;sourceSize.height:800}
    }
    Text {anchors.bottom:parent.bottom;anchors.bottomMargin:20;anchors.horizontalCenter:parent.horizontalCenter;text:root.preview?"Preview · press Space to return":"Slide a neighbor into the empty tile";color:"#b4d5df";font.pixelSize:12}
    Text {anchors.bottom:parent.bottom;anchors.bottomMargin:5;anchors.horizontalCenter:parent.horizontalCenter;text:"Arrows move tiles · Space preview · Esc save · R reshuffle";color:"#7da1b3";font.pixelSize:10}
}
