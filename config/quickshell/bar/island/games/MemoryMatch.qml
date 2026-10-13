import QtQuick
import Quickshell
import "../../../theme"
import "ArcadeLogic.js" as Logic

FocusScope {
    id: root
    property int score: 0
    property bool over: false
    property color tint: Theme.accent
    signal finished(int score)
    property var state: null
    property bool ready: false
    readonly property string resultText: over ? "All pairs found!" : ""
    readonly property int cols: state && state.pairs===12 ? 6 : 4
    readonly property real cw: (width-40-(cols-1)*12)/cols
    readonly property real ch: Math.min(112,(height-118)/Math.ceil((state?state.deck.length:16)/cols)-12)
    readonly property var hues: ["#a795ef","#f0b46b","#64cec4","#ed8b9e","#86bfe8","#b8d47d","#efc968","#a3aee6","#da9bd5","#79cc98","#fa9f80","#9ddbdc"]
    focus: true
    ArcadeStore {id:store;gameId:"memorymatch"}
    function sync(): void {
        over=state.over
        score=Math.max(1,state.matched.filter(v=>v).length*50-state.moves*3-Math.floor(state.seconds/5))
    }
    function saveGame(): void {if(ready)store.save(state)}
    function newSize(pairs: int): void {mismatch.stop();state=Logic.memoryFresh(pairs);ready=true;sync();saveGame()}
    function restart(): void {newSize(state?state.pairs:8)}
    function pick(index: int): void {
        const next=Logic.copy(state)
        if(!Logic.memoryPick(next,index))return
        state=next;sync();saveGame()
        if(state.open.length===2)mismatch.restart()
        if(over)finished(score)
    }
    Component.onCompleted: {
        const saved=store.read()
        if(Logic.memoryValid(saved)){state=saved;ready=true;sync();if(state.open.length===2)mismatch.start()}
        else restart()
    }
    Component.onDestruction: saveGame()
    Timer {
        id:mismatch;interval:850
        onTriggered:{const next=Logic.copy(root.state);next.open=[];root.state=next;root.saveGame()}
    }
    Timer {
        interval:1000;repeat:true;running:root.ready&&!root.over
        onTriggered:{const next=Logic.copy(root.state);next.seconds++;root.state=next;root.sync();if(next.seconds%5===0)root.saveGame()}
    }
    Keys.onEscapePressed: event=>{saveGame();event.accepted=false}
    Rectangle {anchors.fill:parent;radius:18;color:"#151b2c";border.color:"#333d59"}
    Row {
        x:18;y:12;spacing:10
        Image {source:"memory-logo.svg";width:34;height:34}
        Column {
            Text {text:"MEMORY GARDEN";color:"#e5dcff";font.family:Theme.fontFamily;font.bold:true;font.pixelSize:15}
            Text {text:root.state?(root.state.matched.filter(v=>v).length/2)+" / "+root.state.pairs+" pairs · "+root.state.moves+" turns":"";color:"#a6b2ca";font.pixelSize:12}
        }
    }
    Row {
        anchors.right:parent.right;anchors.rightMargin:18;y:15;spacing:6
        Repeater {
            model:[{n:6,label:"12 cards"},{n:8,label:"16 cards"},{n:12,label:"24 cards"}]
            Rectangle {
                required property var modelData
                width:65;height:28;radius:8;color:root.state&&root.state.pairs===modelData.n?"#68598f":"#293449"
                Text {anchors.centerIn:parent;text:parent.modelData.label;color:"#f3eaff";font.pixelSize:10}
                MouseArea {anchors.fill:parent;onClicked:{root.newSize(parent.modelData.n);root.forceActiveFocus()}}
            }
        }
    }
    Item {
        x:20;y:68;width:parent.width-40;height:parent.height-114
        Repeater {
            model:root.state?root.state.deck.length:0
            Item {
                id:card
                required property int index
                readonly property int symbol:root.state?root.state.deck[index]:0
                readonly property bool faceUp:root.state&&(root.state.matched[index]||root.state.open.indexOf(index)>=0)
                readonly property bool matched:root.state&&root.state.matched[index]
                property real turn:faceUp?180:0
                x:(index%root.cols)*(root.cw+12);y:Math.floor(index/root.cols)*(root.ch+12)
                width:root.cw;height:root.ch
                transform:Rotation {origin.x:card.width/2;origin.y:card.height/2;axis.x:0;axis.y:1;axis.z:0;angle:card.turn}
                Behavior on turn {NumberAnimation {duration:240;easing.type:Easing.InOutCubic}}
                Rectangle {
                    anchors.fill:parent;radius:13;y:3;color:"#080e1a"
                }
                Rectangle {
                    anchors.fill:parent;radius:13
                    gradient:Gradient {
                        GradientStop {position:0;color:card.turn>90?"#f1edf8":"#364364"}
                        GradientStop {position:1;color:card.turn>90?"#dcd8ee":"#202b45"}
                    }
                    border.width:card.matched?2:1;border.color:card.matched?"#82d9b8":"#526381"
                    Item {
                        anchors.fill:parent;visible:card.turn<=90
                        Image {anchors.centerIn:parent;source:"memory-logo.svg";width:Math.min(parent.width,parent.height)*.48;height:width;opacity:.8}
                        Rectangle {anchors.fill:parent;anchors.margins:7;radius:9;color:"transparent";border.color:"#556689"}
                    }
                    Item {
                        anchors.fill:parent;visible:card.turn>90
                        transform:Rotation {origin.x:card.width/2;origin.y:card.height/2;axis.x:0;axis.y:1;axis.z:0;angle:180}
                        Rectangle {anchors.centerIn:parent;width:Math.min(parent.width,parent.height)*.67;height:width;radius:width/2;color:root.hues[card.symbol];opacity:.25}
                        Image {anchors.centerIn:parent;width:Math.min(parent.width,parent.height)*.56;height:width;source:"memory-symbol-"+card.symbol+".svg";sourceSize.width:100;sourceSize.height:100}
                        Text {anchors.right:parent.right;anchors.top:parent.top;anchors.margins:7;text:card.matched?"✓":"";color:"#2b8a69";font.pixelSize:15;font.bold:true}
                    }
                }
                MouseArea {anchors.fill:parent;onClicked:{root.pick(card.index);root.forceActiveFocus()}}
            }
        }
    }
    Text {
        anchors.bottom:parent.bottom;anchors.bottomMargin:18;anchors.horizontalCenter:parent.horizontalCenter
        text:"Find matching illustrations · "+(root.state?root.state.seconds:0)+"s · "+store.status;color:"#aab7d0";font.pixelSize:12
    }
    Text {anchors.bottom:parent.bottom;anchors.bottomMargin:4;anchors.horizontalCenter:parent.horizontalCenter;text:"Choose a size to start a fresh board · Esc save · R restart";color:"#7689a8";font.pixelSize:10}
}
