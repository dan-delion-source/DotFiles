.pragma library

// One-suit Spider: 104 cards, ten columns, five stock deals, eight full runs.
function copy(s) { return JSON.parse(JSON.stringify(s)); }
function fresh() {
    var cards = [];
    for (var rank = 1; rank <= 13; rank++)
        for (var n = 0; n < 8; n++) cards.push({rank:rank, faceUp:false});
    for (var i = 103; i > 0; i--) {
        var j = Math.floor(Math.random() * (i+1)), t = cards[i];
        cards[i] = cards[j]; cards[j] = t;
    }
    var s = {version:1, columns:[], stock:[], completed:0, moves:0, over:false};
    for (var c = 0; c < 10; c++) {
        var pile = cards.splice(0, c < 4 ? 6 : 5);
        pile[pile.length-1].faceUp = true;
        s.columns.push(pile);
    }
    s.stock = cards;
    return s;
}
function selectable(pile, index) {
    if (!Number.isInteger(index) || index < 0 || index >= pile.length) return false;
    for (var i=index; i<pile.length; i++) {
        if (!pile[i].faceUp) return false;
        if (i>index && pile[i-1].rank !== pile[i].rank+1) return false;
    }
    return true;
}
function settle(s) {
    for (var c=0; c<10; c++) {
        var pile=s.columns[c];
        if (pile.length) pile[pile.length-1].faceUp=true;
        while (pile.length>=13) {
            var start=pile.length-13;
            if (pile[start].rank!==13 || !selectable(pile,start)) break;
            pile.splice(start,13);s.completed++;
            if (pile.length) pile[pile.length-1].faceUp=true;
        }
    }
    s.over=s.completed===8;
}
function move(s, from, index, to) {
    if (s.over || from===to || from<0 || from>9 || to<0 || to>9) return false;
    var source=s.columns[from], dest=s.columns[to];
    if (!selectable(source,index)) return false;
    if (dest.length && dest[dest.length-1].rank!==source[index].rank+1) return false;
    s.columns[to]=dest.concat(source.splice(index));
    s.moves++;settle(s);return true;
}
function deal(s) {
    if (s.over || s.stock.length<10 || s.columns.some(function(p){return p.length===0;})) return false;
    for (var c=0;c<10;c++) {
        var card=s.stock.pop();card.faceUp=true;s.columns[c].push(card);
    }
    s.moves++;settle(s);return true;
}
function valid(s) {
    if (!s || s.version!==1 || !Array.isArray(s.columns) || s.columns.length!==10
        || !s.columns.every(function(p){return Array.isArray(p);}) || !Array.isArray(s.stock)
        || s.stock.length>50 || s.stock.length%10!==0 || !Number.isInteger(s.completed)
        || s.completed<0 || s.completed>8 || !Number.isInteger(s.moves) || s.moves<0
        || typeof s.over!=='boolean' || s.over!==(s.completed===8)) return false;
    var cards=[].concat.apply([],s.columns).concat(s.stock), counts=Array(14).fill(0);
    if (cards.length+s.completed*13!==104) return false;
    for (var i=0;i<cards.length;i++) {
        var card=cards[i];
        if (!card || !Number.isInteger(card.rank) || card.rank<1 || card.rank>13
            || typeof card.faceUp!=='boolean') return false;
        counts[card.rank]++;
    }
    for (var r=1;r<=13;r++) if (counts[r]+s.completed!==8) return false;
    if (s.stock.some(function(c){return c.faceUp;})) return false;
    return s.columns.every(function(p){
        var up=false;
        for (var i=0;i<p.length;i++) {if(p[i].faceUp)up=true;else if(up)return false;}
        return p.length===0 || p[p.length-1].faceUp;
    });
}
