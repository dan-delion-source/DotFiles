.pragma library

// Neon Breakout — fixed-size simulation, independent of the Qt renderer.
var W = 720, H = 480, R = 5, PADDLE_Y = 442, ECHO_Y = 374;
var COLORS = ["#ff5e93", "#ffb75e", "#ffe78a", "#5cebbd", "#50dfff", "#ac94ff"];
var POWER_TYPES = ["multi", "wide", "echo", "shield", "slow", "laser", "life"];
var POWER_LABELS = {multi:"MULTI BALL",wide:"WIDE PADDLE",echo:"ECHO PLATFORM",shield:"SAFETY NET",slow:"SLOW MOTION",laser:"LASER CANNONS",life:"EXTRA LIFE"};
var POWER_COLORS = {multi:"#ffb75e",wide:"#50dfff",echo:"#ac94ff",shield:"#5cebbd",slow:"#ffe78a",laser:"#ff5e93",life:"#ff91c7"};
var LEVELS = [
 {name:"FIRST CONTACT", rows:["111111111111","111111111111","111111111111","111111111111"]},
 {name:"NEON STAIRWAY", rows:["1..........1","11........11","121......121","1221....1221","12221..12221","111111111111"]},
 {name:"DIAMOND DRIVE", rows:[".....22.....","....2112....","...211112...","..21111112..","...211112...","....2112....",".....22....."]},
 {name:"PIXEL INVADERS", rows:["..1......1..","...1....1...","..22222222..",".2212222122.","222222222222","2.22222222.2","2.2......2.2","...22..22..."]},
 {name:"CHROMA GATES", rows:["222222222222","1..1.##.1..1","1..1....1..1","2..2....2..2","1..1....1..1","1111....1111"]},
 {name:"TWIN CITADELS", rows:[".2.2....2.2.","22222..22222","2#2#2..2#2#2","21112..21112","21112..21112","22222..22222"]},
 {name:"HEART OF GLASS", rows:[".2222..2222.","211112211112","211111111112",".2111111112.","..21111112..","...211112...","....2112....",".....22....."]},
 {name:"SYNTHWAVE", rows:["22..22..22..",".22..22..22.","..22..22..22","11..11..11..",".11..11..11.","..11..11..11","22..22..22..",".22..22..22."]},
 {name:"CIRCUIT BREAKER", rows:["333333333333","2..2....2..2","2##2.##.2##2","2112....2112","...222222...","1111....1111","..22....22.."]},
 {name:"PRISM VAULT", rows:[".....33.....","....3223....","...32##23...","..32111123..",".3211221123.","321122221123",".3211221123.","..32111123.."]},
 {name:"ORBITAL RINGS", rows:["..33333333..",".32......23.","32..2222..23","32.21..12.23","32.21..12.23","32..2222..23",".32......23.","..33333333.."]},
 {name:"GLITCH MATRIX", rows:["3.2.3.2.3.2.",".2.3.2.3.2.3","11##1111##11","22..2222..22","33##3333##33","11..1111..11",".2.3.2.3.2.3","3.2.3.2.3.2."]},
 {name:"SOLAR REACTOR", rows:["3..3.33.3..3",".3.3.33.3.3.","..33333333..","33322##22333","33322##22333","..33333333..",".3.3.33.3.3.","3..3.33.3..3"]},
 {name:"LAST TRANSMISSION", rows:["3333....3333","3223.##.3223","3213....3123","322333333223","333211112333","..32122123..","...322223...","....3333...."]},
 {name:"NEON HORIZON", rows:["333333333333","32..3..3..23","321.2222.123","32##2112##23","322222222223",".3322332233.","..33233233..","...333333..."]}
];

function clamp(x,a,b) { return Math.max(a,Math.min(b,x)); }
function finite(x) { return typeof x === "number" && Number.isFinite(x); }
function integer(x,a,b) { return Number.isInteger(x) && x>=a && x<=b; }
function random(s) { s.rng=(Math.imul(s.rng,1664525)+1013904223)>>>0;return s.rng/4294967296; }
function makeBricks(level) {
 var bricks=[], rows=LEVELS[level-1].rows, bw=(W-48-11*6)/12;
 rows.forEach(function(row,y){for(var x=0;x<row.length;x++){
  var ch=row[x];if(ch!==".")bricks.push({id:y*12+x,x:24+x*(bw+6),y:44+y*25,w:bw,h:18,hp:ch==="#"?-1:Number(ch),max:ch==="#"?-1:Number(ch),color:y%6});
 }});return bricks;
}
function fresh(seed) {
 var s={version:1,game:"neon-breakout",level:1,phase:"serve",score:0,lives:4,rng:(seed===undefined?Date.now():seed)>>>0,nextId:1,
  paddle:W/2,balls:[],bricks:[],drops:[],lasers:[],particles:[],effects:{wide:0,echo:0,slow:0,laser:0},shield:0,
  combo:0,comboClock:0,broken:0,elapsed:0,stageTime:0,laserClock:0,shake:0,flash:0,notice:"",noticeClock:0};
 loadLevel(s,1);return s;
}
function paddleWidth(s) {return s.effects.wide>0?150:102;}
function speed(s) {return Math.min(470,270+s.level*9+Math.min(40,s.stageTime*.16))*(s.effects.slow>0?.7:1);}
function left(s) {return s.bricks.filter(function(b){return b.hp>0;}).length;}
function movePaddle(s,x) {s.paddle=clamp(x,paddleWidth(s)/2+8,W-paddleWidth(s)/2-8);if(s.phase==="serve")s.balls.forEach(function(b){b.x=s.paddle;b.y=PADDLE_Y-R-2;});}
function newBall(s,x,y,vx,vy) {return {id:s.nextId++,x:x,y:y,vx:vx,vy:vy,trail:[]};}
function clearPowers(s) {s.effects={wide:0,echo:0,slow:0,laser:0};s.shield=0;s.drops=[];s.lasers=[];s.laserClock=0;}
function loadLevel(s,n) {
 s.level=n;s.bricks=makeBricks(n);clearPowers(s);s.phase="serve";s.stageTime=0;s.combo=0;s.comboClock=0;s.paddle=W/2;
 s.balls=[newBall(s,s.paddle,PADDLE_Y-R-2,0,0)];s.notice=LEVELS[n-1].name;s.noticeClock=3;
}
function launch(s) {
 if(s.phase==="clear"){loadLevel(s,s.level+1);return true;}
 if(s.phase!=="serve")return false;
 var v=speed(s),angle=(random(s)-.5)*.5;
 s.balls.forEach(function(b){b.vx=Math.sin(angle)*v;b.vy=-Math.cos(angle)*v;});s.phase="play";return true;
}
function burst(s,x,y,color,n) {
 for(var i=0;i<n;i++){var a=random(s)*Math.PI*2,v=35+random(s)*125;s.particles.push({x:x,y:y,vx:Math.cos(a)*v,vy:Math.sin(a)*v,life:.25+random(s)*.35,max:.6,color:color});}
 if(s.particles.length>180)s.particles.splice(0,s.particles.length-180);
}
function announce(s,text) {s.notice=text;s.noticeClock=2.5;}
function applyPower(s,kind) {
 if(POWER_TYPES.indexOf(kind)<0||s.phase!=="play")return false;
 s.score+=75;announce(s,POWER_LABELS[kind]);burst(s,s.paddle,PADDLE_Y,POWER_COLORS[kind],14);
 if(kind==="multi") {
  var first=s.balls[0],v=speed(s);if(first){
   var a=Math.atan2(first.vy,first.vx);
   [-.42,.42].forEach(function(delta){if(s.balls.length<6){var angle=a+delta;s.balls.push(newBall(s,first.x,first.y,Math.cos(angle)*v,-Math.max(v*.32,Math.abs(Math.sin(angle)*v))));}});
  }
 }else if(kind==="shield")s.shield=Math.min(3,s.shield+2);
 else if(kind==="life")s.lives=Math.min(9,s.lives+1);
 else {var duration=kind==="wide"?18:kind==="echo"?20:kind==="slow"?12:14;s.effects[kind]=Math.min(40,s.effects[kind]+duration);}
 movePaddle(s,s.paddle);return true;
}
function hitBrick(s,brick,x,y) {
 if(brick.hp===0)return;
 if(brick.hp<0){burst(s,x,y,"#60718e",3);return;}
 brick.hp--;s.score+=5;s.flash=.045;
 burst(s,x,y,COLORS[brick.color],brick.hp===0?9:4);
 if(brick.hp!==0)return;
 s.broken++;s.combo=Math.min(8,s.combo+1);s.comboClock=3;s.score+=40*brick.max*s.combo;s.shake=.075;
 // A guaranteed drop every seventh destroyed brick supplements random drops.
 if((s.broken%7===0||random(s)<.17)&&s.drops.length<12){
  var k=POWER_TYPES[Math.floor(random(s)*POWER_TYPES.length)];
  s.drops.push({id:s.nextId++,x:brick.x+brick.w/2,y:brick.y+brick.h/2,kind:k});
 }
}
function finishLevel(s) {
 if(left(s)>0||s.phase!=="play")return false;
 s.score+=500+s.level*100+s.lives*50;s.balls=[];s.drops=[];s.lasers=[];s.shake=.2;
 if(s.level===15){s.phase="won";announce(s,"ALL 15 SECTORS CLEARED");}
 else {s.phase="clear";announce(s,"SECTOR COMPLETE");}
 for(var i=0;i<8;i++)burst(s,80+i*80,190+(i%2)*35,COLORS[i%6],15);
 return true;
}
// Circle/rectangle contact: return a separating normal and penetration depth.
function contact(b,box) {
 var qx=clamp(b.x,box.x,box.x+box.w),qy=clamp(b.y,box.y,box.y+box.h),dx=b.x-qx,dy=b.y-qy,d2=dx*dx+dy*dy;
 if(d2>=R*R)return null;
 if(d2>.000001){var d=Math.sqrt(d2);return {nx:dx/d,ny:dy/d,depth:R-d};}
 var distances=[b.x-box.x,box.x+box.w-b.x,b.y-box.y,box.y+box.h-b.y],side=distances.indexOf(Math.min.apply(null,distances));
 return {nx:side===0?-1:side===1?1:0,ny:side===2?-1:side===3?1:0,depth:R+distances[side]};
}
function bounce(s,b,cy,cx,cw,main) {
 if(b.vy<=0||b.y+R<cy||b.y-R>cy+9||b.x+R<cx-cw/2||b.x-R>cx+cw/2)return false;
 var rel=clamp((b.x-cx)/(cw/2),-1,1),angle=rel*1.08,v=speed(s);
 b.y=cy-R-.1;b.vx=Math.sin(angle)*v;b.vy=-Math.cos(angle)*v;
 if(Math.abs(b.vx)<v*.08)b.vx=(rel<0?-1:1)*v*.08;
 if(main){s.combo=0;s.comboClock=0;}burst(s,b.x,cy,main?"#50dfff":"#ac94ff",3);return true;
}
function step(s,dt) {
 var v=speed(s),dead=[];
 for(var j=0;j<s.balls.length;j++) {
  var b=s.balls[j],oldY=b.y,n=Math.hypot(b.vx,b.vy);
  if(n>0){b.vx*=v/n;b.vy*=v/n;}
  b.x+=b.vx*dt;b.y+=b.vy*dt;
  if(b.x<R+4){b.x=R+4;b.vx=Math.abs(b.vx);}else if(b.x>W-R-4){b.x=W-R-4;b.vx=-Math.abs(b.vx);}
  if(b.y<R+4){b.y=R+4;b.vy=Math.abs(b.vy);}
  var pw=paddleWidth(s);
  if(s.effects.echo>0&&oldY<=ECHO_Y+R)bounce(s,b,ECHO_Y,W-s.paddle,pw*.66,false);
  if(oldY<=PADDLE_Y+R)bounce(s,b,PADDLE_Y,s.paddle,pw,true);
  if(s.shield>0&&b.vy>0&&oldY+R< H-12 && b.y+R>=H-12){b.y=H-12-R;b.vy=-Math.abs(b.vy);s.shield--;announce(s,"SAFETY NET SAVED A BALL");burst(s,b.x,H-12,"#5cebbd",12);}
  for(var i=0;i<s.bricks.length;i++) {
   var brick=s.bricks[i];if(brick.hp===0)continue;
   var c=contact(b,brick);if(!c)continue;
   b.x+=c.nx*(c.depth+.02);b.y+=c.ny*(c.depth+.02);
   var dot=b.vx*c.nx+b.vy*c.ny;
   if(dot<0){b.vx-=2*dot*c.nx;b.vy-=2*dot*c.ny;hitBrick(s,brick,b.x,b.y);}
   // Avoid near-horizontal or vertical loops after a side contact.
   if(Math.abs(b.vy)<v*.24)b.vy=(b.vy<0?-1:1)*v*.24;
   if(Math.abs(b.vx)<v*.035)b.vx=(b.vx<0?-1:1)*v*.035;
   break;
  }
  if(b.y>H+R+8)dead.push(b.id);
 }
 if(dead.length)s.balls=s.balls.filter(function(b){return dead.indexOf(b.id)<0;});
 // Laser beams stop at the first brick they meet, including steel.
 for(var l=0;l<s.lasers.length;l++){
  var laser=s.lasers[l],before=laser.y;laser.y-=650*dt;
  var targets=s.bricks.filter(function(br){return br.hp!==0&&laser.x>=br.x&&laser.x<=br.x+br.w&&before>=br.y&&laser.y<=br.y+br.h;});
  if(targets.length){targets.sort(function(a,b){return b.y-a.y;});hitBrick(s,targets[0],laser.x,targets[0].y+targets[0].h);laser.y=-50;}
 }
 s.lasers=s.lasers.filter(function(laser){return laser.y>-10;});
}
function tick(s,dt,input) {
 if(!finite(dt)||dt<=0)return;
 dt=Math.min(.05,dt);input=input||{};
 s.shake=Math.max(0,s.shake-dt);s.flash=Math.max(0,s.flash-dt);s.noticeClock=Math.max(0,s.noticeClock-dt);
 s.particles.forEach(function(p){p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=80*dt;});s.particles=s.particles.filter(function(p){return p.life>0;});
 if(s.phase!=="play"&&s.phase!=="serve")return;
 if(finite(input.x))movePaddle(s,input.x);else if(input.direction)movePaddle(s,s.paddle+clamp(input.direction,-1,1)*620*dt);
 if(s.phase!=="play")return;
 s.elapsed+=dt;s.stageTime+=dt;
 Object.keys(s.effects).forEach(function(k){s.effects[k]=Math.max(0,s.effects[k]-dt);});movePaddle(s,s.paddle);
 s.comboClock=Math.max(0,s.comboClock-dt);if(!s.comboClock)s.combo=0;
 s.balls.forEach(function(b){b.trail.push({x:b.x,y:b.y});if(b.trail.length>7)b.trail.shift();});
 if(s.effects.laser>0){s.laserClock-=dt;if(s.laserClock<=0){s.laserClock=.36;var half=paddleWidth(s)/2-8;[-half,half].forEach(function(offset){s.lasers.push({x:s.paddle+offset,y:PADDLE_Y-5});});}}
 var steps=Math.ceil(dt/.0035);for(var i=0;i<steps&&s.phase==="play";i++){step(s,dt/steps);if(finishLevel(s))return;}
 s.drops=s.drops.filter(function(drop){drop.y+=78*dt;if(drop.y>=PADDLE_Y-10&&drop.y<=PADDLE_Y+18&&Math.abs(drop.x-s.paddle)<paddleWidth(s)/2+13){applyPower(s,drop.kind);return false;}return drop.y<H+20;});
 if(!s.balls.length){
  s.lives--;clearPowers(s);s.combo=0;s.comboClock=0;
  if(s.lives<=0){s.lives=0;s.phase="lost";announce(s,"END OF TRANSMISSION");}
  else {s.phase="serve";s.balls=[newBall(s,s.paddle,PADDLE_Y-R-2,0,0)];announce(s,"BALL LOST // TRY AGAIN");}
 }
}
function snapshot(s) {
 var out=JSON.parse(JSON.stringify(s));out.particles=[];out.shake=0;out.flash=0;out.balls.forEach(function(b){b.trail=[];});return out;
}
function valid(s) {
 if(!s||s.version!==1||s.game!=="neon-breakout"||!integer(s.level,1,15)||["serve","play","clear","won","lost"].indexOf(s.phase)<0||!integer(s.score,0,2000000000)||!integer(s.lives,0,9)||!integer(s.rng,0,4294967295)||!integer(s.nextId,1,2000000000)||!finite(s.paddle)||s.paddle<0||s.paddle>W||!integer(s.shield,0,3)||!integer(s.combo,0,8)||!integer(s.broken,0,2000))return false;
 if(![s.elapsed,s.stageTime,s.comboClock,s.laserClock,s.shake,s.flash,s.noticeClock].every(function(v){return finite(v)&&v>=0&&v<100000000;})||typeof s.notice!=="string"||s.notice.length>100)return false;
 if(!s.effects||!["wide","echo","slow","laser"].every(function(k){return finite(s.effects[k])&&s.effects[k]>=0&&s.effects[k]<=40;}))return false;
 if(!Array.isArray(s.bricks)||!Array.isArray(s.balls)||s.balls.length>6||!Array.isArray(s.drops)||s.drops.length>12||!Array.isArray(s.lasers)||s.lasers.length>100||!Array.isArray(s.particles)||s.particles.length>180)return false;
 var ref=makeBricks(s.level);if(s.bricks.length!==ref.length||!s.bricks.every(function(b,i){var r=ref[i];return b&&b.id===r.id&&["x","y","w","h","max","color"].every(function(k){return b[k]===r[k];})&&integer(b.hp,r.max<0?-1:0,r.max);}))return false;
 var ids={};if(!s.balls.every(function(b){if(!b||!integer(b.id,1,s.nextId-1)||ids[b.id]||![b.x,b.y,b.vx,b.vy].every(finite)||b.x<0||b.x>W||b.y<0||b.y>H+14||Math.abs(b.vx)>1200||Math.abs(b.vy)>1200||!Array.isArray(b.trail)||b.trail.length>7)return false;ids[b.id]=true;return s.phase==="serve"?(b.vx===0&&b.vy===0):Math.hypot(b.vx,b.vy)>0;}))return false;
 if(!s.drops.every(function(d){return d&&integer(d.id,1,s.nextId-1)&&finite(d.x)&&d.x>=0&&d.x<=W&&finite(d.y)&&d.y>=0&&d.y<=H+20&&POWER_TYPES.indexOf(d.kind)>=0;}))return false;
 if(!s.lasers.every(function(l){return l&&finite(l.x)&&l.x>=0&&l.x<=W&&finite(l.y)&&l.y>=-10&&l.y<=H;}))return false;
 if(s.phase==="serve"&&(s.balls.length!==1||s.lives<1))return false;
 if(s.phase==="play"&&(!s.balls.length||s.lives<1||left(s)===0))return false;
 if((s.phase==="clear"||s.phase==="won")&&(left(s)!==0||s.balls.length))return false;
 if(s.phase==="clear"&&s.level===15||s.phase==="won"&&s.level!==15||s.phase==="lost"&&(s.lives!==0||s.balls.length))return false;
 return true;
}
