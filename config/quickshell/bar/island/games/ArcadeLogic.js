.pragma library

function copy(s) {return JSON.parse(JSON.stringify(s));}
function shuffle(a) {for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1)),t=a[i];a[i]=a[j];a[j]=t;}return a;}
function memoryFresh(pairs) {
 var deck=[];for(var i=0;i<pairs;i++)deck.push(i,i);
 return {version:1,type:'memory',pairs:pairs,deck:shuffle(deck),matched:Array(pairs*2).fill(false),open:[],moves:0,seconds:0,over:false};
}
function memoryPick(s,i) {
 if(s.over||s.open.length>=2||s.matched[i]||s.open.indexOf(i)>=0||i<0||i>=s.deck.length)return false;
 s.open.push(i);
 if(s.open.length===2){s.moves++;if(s.deck[s.open[0]]===s.deck[s.open[1]]){s.matched[s.open[0]]=true;s.matched[s.open[1]]=true;s.open=[];s.over=s.matched.every(function(v){return v;});}}
 return true;
}
function memoryValid(s) {
 if(!s||s.version!==1||s.type!=='memory'||![6,8,12].includes(s.pairs)||!Array.isArray(s.deck)||s.deck.length!==s.pairs*2||!Array.isArray(s.matched)||s.matched.length!==s.deck.length||!s.matched.every(function(v){return typeof v==='boolean';})||!Array.isArray(s.open)||s.open.length>2||!Number.isInteger(s.moves)||s.moves<0||!Number.isInteger(s.seconds)||s.seconds<0||typeof s.over!=='boolean')return false;
 for(var i=0;i<s.pairs;i++){var ids=[];for(var j=0;j<s.deck.length;j++)if(s.deck[j]===i)ids.push(j);if(ids.length!==2||s.matched[ids[0]]!==s.matched[ids[1]])return false;}
 return s.deck.every(function(v){return Number.isInteger(v)&&v>=0&&v<s.pairs;})&&s.open.every(function(v,i){return Number.isInteger(v)&&v>=0&&v<s.deck.length&&!s.matched[v]&&s.open.indexOf(v)===i;})&&s.over===s.matched.every(function(v){return v;});
}
function puzzleFresh(n) {
 var a=[];for(var i=1;i<n*n;i++)a.push(i);a.push(0);
 var blank=a.length-1,last=-1;
 for(var k=0;k<400;k++) {
  var r=Math.floor(blank/n),c=blank%n,opts=[];
  if(r>0)opts.push(blank-n);if(r<n-1)opts.push(blank+n);if(c>0)opts.push(blank-1);if(c<n-1)opts.push(blank+1);
  opts=opts.filter(function(i){return i!==last;});var to=opts[Math.floor(Math.random()*opts.length)];a[blank]=a[to];a[to]=0;last=blank;blank=to;
 }
 if(a.every(function(v,i){return v===(i+1)%(n*n);})){a[blank]=a[blank-1];a[blank-1]=0;}
 return {version:1,type:'puzzle',n:n,tiles:a,moves:0,seconds:0,over:false};
}
function puzzleMove(s,index) {
 if(s.over||index<0||index>=s.tiles.length)return false;
 var b=s.tiles.indexOf(0);if(Math.abs(Math.floor(b/s.n)-Math.floor(index/s.n))+Math.abs(b%s.n-index%s.n)!==1)return false;
 s.tiles[b]=s.tiles[index];s.tiles[index]=0;s.moves++;s.over=s.tiles.every(function(v,i){return v===(i+1)%(s.n*s.n);});return true;
}
function puzzleValid(s) {
 if(!s||s.version!==1||s.type!=='puzzle'||![3,4,5].includes(s.n)||!Array.isArray(s.tiles)||s.tiles.length!==s.n*s.n||!s.tiles.every(function(v){return Number.isInteger(v)&&v>=0&&v<s.n*s.n;})||new Set(s.tiles).size!==s.tiles.length||!Number.isInteger(s.moves)||s.moves<0||!Number.isInteger(s.seconds)||s.seconds<0||typeof s.over!=='boolean')return false;
 var inv=0;for(var i=0;i<s.tiles.length;i++)for(var j=i+1;j<s.tiles.length;j++)if(s.tiles[i]&&s.tiles[j]&&s.tiles[i]>s.tiles[j])inv++;
 var rowFromBottom=s.n-Math.floor(s.tiles.indexOf(0)/s.n);
 return (s.n%2?inv%2===0:(inv+rowFromBottom)%2===1)&&s.over===s.tiles.every(function(v,i){return v===(i+1)%(s.n*s.n);});
}

// Bubble coordinates are measured in cell pitches. Twelve columns, odd rows offset.
var bubbleCols=12,bubbleRows=12;
function bubblePos(i){var row=Math.floor(i/bubbleCols);return {x:i%bubbleCols+0.5+(row%2)*0.5,y:0.6+row*0.8660254};}
function bubbleNeighbors(i) {
 var r=Math.floor(i/12),c=i%12,out=[],shift=r%2?1:-1;
 [[r,c-1],[r,c+1],[r-1,c],[r-1,c+shift],[r+1,c],[r+1,c+shift]].forEach(function(p){if(p[0]>=0&&p[0]<12&&p[1]>=0&&p[1]<12)out.push(p[0]*12+p[1]);});return out;
}
function bubbleColor(s){var colors=[];s.grid.forEach(function(v){if(v>=0&&colors.indexOf(v)<0)colors.push(v);});return colors.length?colors[Math.floor(Math.random()*colors.length)]:0;}
function bubbleLevel(s){s.grid=Array(144).fill(-1);for(var i=0;i<(4+Math.min(s.level,3))*12;i++)s.grid[i]=Math.floor(Math.random()*Math.min(6,3+s.level));s.shots=0;s.ball=null;s.current=bubbleColor(s);s.next=bubbleColor(s);}
function bubbleFresh(){var s={version:1,type:'bubble',level:1,score:0,shots:0,grid:[],current:0,next:0,ball:null,over:false,won:false};bubbleLevel(s);return s;}
function bubbleShoot(s,angle){if(s.over||s.ball)return false;angle=Math.max(-2.9,Math.min(-0.24,angle));s.ball={x:6.25,y:12.25,vx:Math.cos(angle)*17,vy:Math.sin(angle)*17,color:s.current};s.current=s.next;s.next=bubbleColor(s);return true;}
function bubbleAttach(s,hit) {
 var b=s.ball,choices=hit<0?Array.from({length:12},function(_,i){return i;}):bubbleNeighbors(hit);
 choices=choices.filter(function(i){return s.grid[i]<0;});
 if(!choices.length){s.over=true;s.ball=null;return;}
 choices.sort(function(i,j){var p=bubblePos(i),q=bubblePos(j);return Math.hypot(p.x-b.x,p.y-b.y)-Math.hypot(q.x-b.x,q.y-b.y);});
 var slot=choices[0];s.grid[slot]=b.color;s.ball=null;s.shots++;
 var cluster=[slot],seen={};seen[slot]=true;
 for(var at=0;at<cluster.length;at++)bubbleNeighbors(cluster[at]).forEach(function(i){if(!seen[i]&&s.grid[i]===s.grid[slot]){seen[i]=true;cluster.push(i);}});
 if(cluster.length>=3){cluster.forEach(function(i){s.grid[i]=-1;});s.score+=cluster.length*10;
  var anchored=[],visited={};for(var i=0;i<12;i++)if(s.grid[i]>=0){anchored.push(i);visited[i]=true;}
  for(var a=0;a<anchored.length;a++)bubbleNeighbors(anchored[a]).forEach(function(i){if(!visited[i]&&s.grid[i]>=0){visited[i]=true;anchored.push(i);}});
  for(var k=0;k<144;k++)if(s.grid[k]>=0&&!visited[k]){s.grid[k]=-1;s.score+=20;}
 }
 if(s.grid.every(function(v){return v<0;})){
  s.score+=500;if(s.level===5){s.over=true;s.won=true;}else{s.level++;bubbleLevel(s);}return;
 }
 if(s.shots%6===0){if(s.grid.slice(132).some(function(v){return v>=0;})){s.over=true;return;}s.grid=Array.from({length:12},function(){return Math.floor(Math.random()*Math.min(6,3+s.level));}).concat(s.grid.slice(0,132));}
 if(s.grid.slice(120).some(function(v){return v>=0;}))s.over=true;
 s.current=s.grid.indexOf(s.current)>=0?s.current:bubbleColor(s);s.next=s.grid.indexOf(s.next)>=0?s.next:bubbleColor(s);
}
function bubbleTick(s,dt) {
 if(!s.ball||s.over)return;
 // Substeps prevent fast shots tunneling through bubbles.
 var steps=Math.max(1,Math.ceil(dt/0.006)),delta=dt/steps;
 for(var k=0;k<steps&&s.ball;k++) {
  var b=s.ball;b.x+=b.vx*delta;b.y+=b.vy*delta;
  if(b.x<0.45){b.x=0.45;b.vx=Math.abs(b.vx);}if(b.x>12.05){b.x=12.05;b.vx=-Math.abs(b.vx);}
  if(b.y<=0.6){bubbleAttach(s,-1);break;}
  var hit=-1,best=Infinity;
  for(var i=0;i<144;i++)if(s.grid[i]>=0){var p=bubblePos(i),d=Math.hypot(b.x-p.x,b.y-p.y);if(d<0.9&&d<best){hit=i;best=d;}}
  if(hit>=0)bubbleAttach(s,hit);
 }
}
function bubbleValid(s){return !!s&&s.version===1&&s.type==='bubble'&&Number.isInteger(s.level)&&s.level>=1&&s.level<=5&&Number.isInteger(s.score)&&s.score>=0&&Number.isInteger(s.shots)&&s.shots>=0&&Array.isArray(s.grid)&&s.grid.length===144&&s.grid.every(function(v){return Number.isInteger(v)&&v>=-1&&v<6;})&&[s.current,s.next].every(function(v){return Number.isInteger(v)&&v>=0&&v<6;})&&typeof s.over==='boolean'&&typeof s.won==='boolean'&&(!s.won||s.over)&&(!s.ball||[s.ball.x,s.ball.y,s.ball.vx,s.ball.vy].every(Number.isFinite)&&Number.isInteger(s.ball.color)&&s.ball.color>=0&&s.ball.color<6);}

// Tower-defense path and build pads in normalized coordinates.
var path=[{x:0,y:.22},{x:.24,y:.22},{x:.24,y:.7},{x:.52,y:.7},{x:.52,y:.3},{x:.78,y:.3},{x:.78,y:.78},{x:1,y:.78}];
var pads=[{x:.12,y:.38},{x:.12,y:.12},{x:.35,y:.38},{x:.35,y:.82},{x:.43,y:.57},{x:.63,y:.55},{x:.64,y:.16},{x:.88,y:.44},{x:.89,y:.9},{x:.67,y:.85}];
function pathLength(){var n=0;for(var i=1;i<path.length;i++)n+=Math.hypot(path[i].x-path[i-1].x,path[i].y-path[i-1].y);return n;}
function pointAt(progress){var remaining=progress*pathLength();for(var i=1;i<path.length;i++){var a=path[i-1],b=path[i],len=Math.hypot(b.x-a.x,b.y-a.y);if(remaining<=len){var t=remaining/len;return {x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t};}remaining-=len;}return path[path.length-1];}
var towerKinds=[{name:'Arrow',cost:65,damage:18,rate:.65,range:.2},{name:'Frost',cost:90,damage:10,rate:.95,range:.23},{name:'Cannon',cost:120,damage:42,rate:1.45,range:.25}];
function towerFresh(){return {version:1,type:'tower',wave:0,cash:180,lives:15,score:0,towers:[],enemies:[],shots:[],spawn:0,spawnClock:0,active:false,over:false,won:false,nextId:1};}
function towerBuild(s,pad,kind){if(s.over||pad<0||pad>=pads.length||kind<0||kind>2||s.towers.some(function(t){return t.pad===pad;})||s.cash<towerKinds[kind].cost)return false;s.cash-=towerKinds[kind].cost;s.towers.push({pad:pad,kind:kind,level:1,cooldown:0});return true;}
function towerUpgrade(s,pad){var t=s.towers.find(function(t){return t.pad===pad;});if(!t||t.level>=3||s.over)return false;var cost=Math.floor(towerKinds[t.kind].cost*.75*t.level);if(s.cash<cost)return false;s.cash-=cost;t.level++;return true;}
function towerSell(s,pad){var t=s.towers.find(function(t){return t.pad===pad;});if(!t||s.over)return false;s.cash+=Math.floor(towerKinds[t.kind].cost*.6*t.level);s.towers=s.towers.filter(function(x){return x.pad!==pad;});return true;}
function towerWave(s){if(s.over||s.active||s.wave>=10)return false;s.wave++;s.spawn=7+s.wave*2;s.spawnClock=0;s.active=true;return true;}
function towerTick(s,dt){
 if(!s.active||s.over)return;
 s.shots=s.shots.map(function(p){p.life-=dt;return p;}).filter(function(p){return p.life>0;});
 s.spawnClock-=dt;
 if(s.spawn>0&&s.spawnClock<=0){var boss=s.wave%5===0&&s.spawn===1,hp=(50+s.wave*22)*(boss?5:1);s.enemies.push({id:s.nextId++,progress:0,hp:hp,maxHp:hp,speed:(.038+s.wave*.0015)*(boss?.7:1),slow:0,boss:boss});s.spawn--;s.spawnClock=.8;}
 s.enemies.forEach(function(e){e.slow=Math.max(0,e.slow-dt);e.progress+=e.speed*(e.slow>0?.55:1)*dt;});
 s.enemies=s.enemies.filter(function(e){if(e.progress>=1){s.lives-=e.boss?3:1;return false;}return true;});
 s.towers.forEach(function(t){
  t.cooldown=Math.max(0,t.cooldown-dt);if(t.cooldown>0)return;
  var spec=towerKinds[t.kind],range=spec.range+(t.level-1)*.018,p=pads[t.pad];
  var targets=s.enemies.filter(function(e){var q=pointAt(e.progress);return e.hp>0&&Math.hypot(p.x-q.x,p.y-q.y)<=range;}).sort(function(a,b){return b.progress-a.progress;});
  if(!targets.length)return;var e=targets[0],q=pointAt(e.progress),damage=spec.damage*(1+(t.level-1)*.65);e.hp-=damage;if(t.kind===1)e.slow=2;
  if(t.kind===2)s.enemies.forEach(function(other){var o=pointAt(other.progress);if(other!==e&&Math.hypot(q.x-o.x,q.y-o.y)<.08)other.hp-=damage*.5;});
  s.shots.push({x:p.x,y:p.y,tx:q.x,ty:q.y,life:.16,kind:t.kind});t.cooldown=spec.rate/(1+(t.level-1)*.15);
 });
 s.enemies=s.enemies.filter(function(e){if(e.hp<=0){s.cash+=e.boss?45:12;s.score+=e.boss?150:25;return false;}return true;});
 if(s.lives<=0){s.lives=0;s.over=true;s.active=false;return;}
 if(!s.spawn&&!s.enemies.length){s.active=false;s.cash+=45+s.wave*5;s.score+=100;if(s.wave===10){s.over=true;s.won=true;s.score+=1000;}}
}
function towerValid(s){
 if(!s||s.version!==1||s.type!=='tower'||!Number.isInteger(s.wave)||s.wave<0||s.wave>10||!Number.isInteger(s.cash)||s.cash<0||!Number.isInteger(s.lives)||s.lives<0||s.lives>15||!Number.isInteger(s.score)||s.score<0||!Number.isInteger(s.spawn)||s.spawn<0||s.spawn>27||!Number.isFinite(s.spawnClock)||typeof s.active!=='boolean'||typeof s.over!=='boolean'||typeof s.won!=='boolean'||!Number.isInteger(s.nextId)||s.nextId<1||!Array.isArray(s.towers)||s.towers.length>10||!Array.isArray(s.enemies)||s.enemies.length>30||!Array.isArray(s.shots))return false;
 var used={};if(!s.towers.every(function(t){if(!t||!Number.isInteger(t.pad)||t.pad<0||t.pad>=10||used[t.pad]||!Number.isInteger(t.kind)||t.kind<0||t.kind>2||!Number.isInteger(t.level)||t.level<1||t.level>3||!Number.isFinite(t.cooldown))return false;used[t.pad]=true;return true;}))return false;
 return s.enemies.every(function(e){return e&&Number.isInteger(e.id)&&e.id>0&&Number.isFinite(e.progress)&&e.progress>=0&&e.progress<1&&Number.isFinite(e.hp)&&e.hp>0&&Number.isFinite(e.maxHp)&&e.maxHp>=e.hp&&Number.isFinite(e.speed)&&e.speed>0&&Number.isFinite(e.slow)&&e.slow>=0&&typeof e.boss==='boolean';})&&s.shots.every(function(p){return p&&[p.x,p.y,p.tx,p.ty,p.life].every(Number.isFinite)&&Number.isInteger(p.kind)&&p.kind>=0&&p.kind<=2;})&&(!s.won||s.over&&s.wave===10)&&(!s.over||!s.active);
}
