.pragma library

// Original maze-chase implementation for Impasto. No external art assets.
var maze = [
 '###################',
 '#........#........#',
 '#.##.###.#.###.##.#',
 '#o##.###.#.###.##o#',
 '#.................#',
 '#.##.#.#####.#.##.#',
 '#....#...#...#....#',
 '####.###.#.###.####',
 '#....#.......#....#',
 '#.##.#.##.##.#.##.#',
 '#.................#',
 '#.##.#.#####.#.##.#',
 '#....#...#...#....#',
 '####.###.#.###.####',
 '#........#........#',
 '#.##.###.#.###.##.#',
 '#o.#...........#.o#',
 '#....#...#...#....#',
 '###################'
];
var dirs = [{x:1,y:0},{x:0,y:1},{x:-1,y:0},{x:0,y:-1}];
function open(x,y) { return y>=0 && y<maze.length && x>=0 && x<maze[0].length && maze[y][x]!=='#'; }
function fresh() {
 var s={version:1,level:1,score:0,lives:3,over:false,pellets:[],player:{x:9,y:16,dir:2},ghosts:[],power:0,invulnerable:0,tick:0};
 level(s); return s;
}
function actors(s) {
 s.player={x:9,y:16,dir:2};
 s.ghosts=[{x:8,y:8,dir:0},{x:9,y:8,dir:1},{x:10,y:8,dir:2},{x:9,y:9,dir:3}];
 s.power=0; s.invulnerable=18;
}
function level(s) {
 s.pellets=[];
 for(var y=0;y<maze.length;y++) for(var x=0;x<maze[0].length;x++)
  if(open(x,y) && !(x===9 && y===16)) s.pellets.push({x:x,y:y,power:maze[y][x]==='o'});
 actors(s);
}
function distance(tx,ty) {
 var d={}, q=[{x:tx,y:ty}]; d[tx+','+ty]=0;
 for(var i=0;i<q.length;i++) {
  var p=q[i];
  for(var j=0;j<4;j++) {var x=p.x+dirs[j].x,y=p.y+dirs[j].y,k=x+','+y;
   if(open(x,y) && d[k]===undefined) {d[k]=d[p.x+','+p.y]+1;q.push({x:x,y:y});}
  }
 }
 return d;
}
function collision(s) {
 for(var i=0;i<s.ghosts.length;i++) {var g=s.ghosts[i];
  if(g.x!==s.player.x || g.y!==s.player.y) continue;
  if(s.power>0) {s.score+=200;g.x=8+i%3;g.y=8;}
  else if(s.invulnerable<=0) {s.lives--;s.over=s.lives<=0;if(!s.over) actors(s);return true;}
 }
 return false;
}
function step(s,wanted) {
 if(s.over) return;
 s.tick++;s.power=Math.max(0,s.power-1);s.invulnerable=Math.max(0,s.invulnerable-1);
 var p=s.player;
 if(Number.isInteger(wanted) && wanted>=0 && wanted<4 && open(p.x+dirs[wanted].x,p.y+dirs[wanted].y)) p.dir=wanted;
 var v=dirs[p.dir]; if(open(p.x+v.x,p.y+v.y)) {p.x+=v.x;p.y+=v.y;}
 s.pellets=s.pellets.filter(function(c){
  if(c.x!==p.x || c.y!==p.y) return true;
  s.score+=c.power?50:10;if(c.power) s.power=Math.max(35,70-s.level*2);return false;
 });
 if(collision(s)) return;
 if(!s.pellets.length) {s.level++;s.score+=500;level(s);return;}
 // Frightened ghosts move at half speed; normal ghosts occasionally rest.
 if((s.power>0 && s.tick%2===0) || (s.power===0 && s.tick%(Math.max(4,9-s.level))===0)) return;
 var d=distance(p.x,p.y);
 for(var i=0;i<s.ghosts.length;i++) {
  var g=s.ghosts[i], options=[];
  for(var j=0;j<4;j++) if(open(g.x+dirs[j].x,g.y+dirs[j].y)) options.push(j);
  var forward=options.filter(function(n){return n!==(g.dir+2)%4;}); if(forward.length) options=forward;
  options.sort(function(a,b){
   var da=d[(g.x+dirs[a].x)+','+(g.y+dirs[a].y)],db=d[(g.x+dirs[b].x)+','+(g.y+dirs[b].y)];
   return s.power>0?db-da:da-db;
  });
  // Distinct personalities: chaser, roamer and two mixed strategies.
  var random=i===1?0.6:i===0?0.05:0.28;
  var choice=Math.random()<random?options[Math.floor(Math.random()*options.length)]:options[0];
  g.dir=choice;g.x+=dirs[choice].x;g.y+=dirs[choice].y;
 }
 collision(s);
}
function valid(s) {
 function actor(a) {return a && Number.isInteger(a.x)&&Number.isInteger(a.y)&&open(a.x,a.y)&&Number.isInteger(a.dir)&&a.dir>=0&&a.dir<4;}
 if(!s || s.version!==1 || !Number.isInteger(s.level)||s.level<1 || !Number.isInteger(s.score)||s.score<0
  || !Number.isInteger(s.lives)||s.lives<0||s.lives>3 || typeof s.over!=='boolean'||s.over!==(s.lives===0)
  || !actor(s.player)||!Array.isArray(s.ghosts)||s.ghosts.length!==4||!s.ghosts.every(actor)
  || !Number.isInteger(s.power)||s.power<0||!Number.isInteger(s.invulnerable)||s.invulnerable<0
  || !Number.isInteger(s.tick)||s.tick<0||!Array.isArray(s.pellets)||s.pellets.length>361) return false;
 var seen={};
 return s.pellets.every(function(p){
  if(!p||!Number.isInteger(p.x)||!Number.isInteger(p.y)||!open(p.x,p.y)||typeof p.power!=='boolean')return false;
  var k=p.x+','+p.y;if(seen[k])return false;seen[k]=true;return true;
 });
}
