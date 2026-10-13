// Spider Solitaire for Impasto, one suit. Original code and vector logo.
import QtQuick
import Quickshell
import Quickshell.Io
import "../../../theme"
import "../../../services"
import "SpiderLogic.js" as Logic

FocusScope {
    id: root
    property int score: 0
    property bool over: false
    property color tint: Theme.accent
    signal finished(int score)
    property var state: null
    property var history: []
    property int revision: 0
    property int selectedColumn: -1
    property int selectedIndex: -1
    property bool initialized: false
    property string message: "Click a run, then its destination."
    property string saveStatus: ""
    readonly property int completed: { void revision; return state ? state.completed : 0 }
    readonly property int deals: { void revision; return state ? state.stock.length/10 : 0 }
    readonly property real gap: 8
    readonly property real cardWidth: Math.max(20,(width-32-9*gap)/10)
    readonly property real cardHeight: cardWidth*1.38
    readonly property var ranks: ["","A","2","3","4","5","6","7","8","9","10","J","Q","K"]
    readonly property var columns: { void revision; return state ? Logic.copy(state).columns : [] }
    focus: true

    readonly property FileView saveFile: FileView {
        path: `${SettingsService.stateDirectory}/spider-save.json`
        blockLoading: true
        blockWrites: true
        atomicWrites: true
        onSaved: root.saveStatus="Saved"
        onSaveFailed: error => {
            root.saveStatus="Save failed"
            console.warn("Spider save failed:",error)
        }
    }
    function saveGame(): void {
        if(initialized && state) saveFile.setText(JSON.stringify({version:1,game:state,history:history})+"\n")
    }
    function update(): void {
        revision++
        score=state.moves
        over=state.over
        selectedColumn=-1;selectedIndex=-1
    }
    function restart(): void {
        state=Logic.fresh();history=[];initialized=true
        message="One suit · Build eight King-to-Ace runs."
        update();saveGame()
    }
    function remember(): void {
        history=history.concat([Logic.copy(state)]).slice(-30)
    }
    function changed(): void {
        update();saveGame()
        if(over) finished(score)
    }
    function undo(): void {
        if(!history.length || over) return
        state=Logic.copy(history[history.length-1]);history=history.slice(0,-1)
        message="Move undone.";update();saveGame()
    }
    function deal(): void {
        if(over || !deals) return
        if(state.columns.some(p=>p.length===0)) {
            message="Fill every empty column before dealing.";return
        }
        remember();Logic.deal(state);message="Ten new cards dealt.";changed()
    }
    function tap(column: int,index: int): void {
        if(over) return
        if(selectedColumn>=0 && selectedColumn!==column) {
            const prior=Logic.copy(state)
            if(Logic.move(state,selectedColumn,selectedIndex,column)) {
                history=history.concat([prior]).slice(-30)
                message="Build descending runs; any run fits an empty column."
                changed();return
            }
        }
        if(selectedColumn===column && selectedIndex===index) {
            selectedColumn=-1;selectedIndex=-1;return
        }
        if(Logic.selectable(state.columns[column],index)) {
            selectedColumn=column;selectedIndex=index
            message="Select another column to move this run."
        } else {
            selectedColumn=-1;selectedIndex=-1
            message="Only a face-up descending run can move together."
        }
    }
    Component.onCompleted: {
        try {
            const saved=JSON.parse(saveFile.text())
            if(saved.version===1 && Logic.valid(saved.game)) {
                state=saved.game
                history=Array.isArray(saved.history)?saved.history.filter(s=>Logic.valid(s)).slice(-30):[]
                initialized=true;update();return
            }
        } catch(error) { /* Missing or invalid save: new deal. */ }
        restart()
    }
    Component.onDestruction: saveGame()
    Keys.onPressed: event => {
        if(event.key===Qt.Key_Space) deal()
        else if(event.key===Qt.Key_U || (event.key===Qt.Key_Z && (event.modifiers & Qt.ControlModifier))) undo()
        else if(event.key===Qt.Key_Escape) {saveGame();event.accepted=false;return}
        else return // R is handled by GamesPanel.
        event.accepted=true
    }

    Rectangle {
        anchors.fill: parent;radius: Theme.radiusMedium
        gradient: Gradient {
            GradientStop {position:0;color:"#172d32"}
            GradientStop {position:1;color:"#0c1a22"}
        }
        border.color:"#36535d"
    }
    Row {
        x:16;y:8;spacing:10
        Image {width:30;height:30;source:"spider-logo.svg";sourceSize.width:60;sourceSize.height:60}
        Column {
            Text {text:"SPIDER SOLITAIRE";color:"#eee7ff";font.family:Theme.fontFamily;font.pixelSize:13;font.bold:true}
            Text {text:"One suit  ·  "+root.completed+" / 8 runs  ·  "+root.saveStatus;color:"#b9b0cf";font.pixelSize:11}
        }
    }
    Row {
        anchors.right:parent.right;anchors.rightMargin:16;y:8;spacing:8
        Rectangle {
            width:70;height:30;radius:8;color:undoMouse.containsMouse?"#384852":"#253740"
            opacity:root.history.length && !root.over?1:0.4
            Text {anchors.centerIn:parent;text:"Undo";color:"#eee7ff";font.pixelSize:12}
            MouseArea {id:undoMouse;anchors.fill:parent;hoverEnabled:true;onClicked:{root.undo();root.forceActiveFocus()}}
        }
        Rectangle {
            width:105;height:30;radius:8;color:stockMouse.containsMouse?"#504273":"#372e53"
            opacity:root.deals && !root.over?1:0.4
            Text {anchors.centerIn:parent;text:"Deal · "+root.deals;color:"#eee7ff";font.pixelSize:12}
            MouseArea {id:stockMouse;anchors.fill:parent;hoverEnabled:true;onClicked:{root.deal();root.forceActiveFocus()}}
        }
    }
    Flickable {
        id:table
        x:16;y:52;width:parent.width-32;height:parent.height-92
        clip:true;boundsBehavior:Flickable.StopAtBounds
        contentWidth:width
        contentHeight: Math.max(height,root.columns.reduce((h,p)=>Math.max(h, p.length? (p.length-1)*24+root.cardHeight+8:root.cardHeight),0))
        Repeater {
            model:root.columns
            Item {
                id:column
                required property int index
                required property var modelData
                x:index*(root.cardWidth+root.gap)
                width:root.cardWidth
                height:Math.max(root.cardHeight,(modelData.length-1)*24+root.cardHeight)
                Rectangle {
                    width:root.cardWidth;height:root.cardHeight;radius:7;color:"#12252c";border.color:"#51707b"
                    Text {anchors.centerIn:parent;text:"♠";color:"#3d5965";font.pixelSize:24}
                    MouseArea {anchors.fill:parent;onClicked:root.tap(column.index,-1)}
                }
                Repeater {
                    model:column.modelData
                    Rectangle {
                        id:card
                        required property int index
                        required property var modelData
                        readonly property bool chosen:root.selectedColumn===column.index && index>=root.selectedIndex
                        y:index*24;width:root.cardWidth;height:root.cardHeight;radius:7
                        color:modelData.faceUp?"#f2ede3":"#493c70"
                        border.width:chosen?3:1
                        border.color:chosen?"#c6a7ff":modelData.faceUp?"#b4aca2":"#8170a6"
                        Text {
                            x:6;y:3;visible:card.modelData.faceUp
                            text:root.ranks[card.modelData.rank]+"♠";color:"#20202b"
                            font.family:Theme.fontFamily;font.pixelSize:Math.min(15,root.cardWidth/4);font.bold:true
                        }
                        Text {
                            anchors.centerIn:parent;visible:card.modelData.faceUp
                            text:"♠";color:"#282436";font.pixelSize:root.cardWidth*0.45
                        }
                        Image {
                            anchors.centerIn:parent;visible:!card.modelData.faceUp
                            width:root.cardWidth*0.6;height:width;source:"spider-logo.svg"
                        }
                        MouseArea {anchors.fill:parent;onClicked:{root.tap(column.index,card.index);root.forceActiveFocus()}}
                    }
                }
            }
        }
    }
    Text {
        x:16;y:parent.height-34;width:parent.width-32;elide:Text.ElideRight
        text:root.message;color:"#d0c7df";font.pixelSize:12
    }
    Text {
        anchors.bottom:parent.bottom;anchors.bottomMargin:5;anchors.horizontalCenter:parent.horizontalCenter
        text:"Space deal  ·  U / Ctrl+Z undo  ·  Esc save & leave  ·  R new game"
        color:"#879dab";font.pixelSize:11
    }
}
