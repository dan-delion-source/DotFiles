.pragma library

function normalize(edge) {
    return ["top", "left", "right", "bottom"].indexOf(edge) >= 0 ? edge : "top";
}
function vertical(edge) { return edge === "left" || edge === "right"; }
function barHeight(value) {
    return typeof value === "number" && isFinite(value)
        ? Math.max(24, Math.min(48, Math.round(value))) : 32;
}
function sideWidth(value) {
    return typeof value === "number" && isFinite(value)
        ? Math.max(30, Math.min(120, Math.round(value))) : 56;
}
function thickness(edge, capsule, width) {
    return vertical(edge) ? sideWidth(width) : capsule;
}
function popup(edge, screenWidth, screenHeight, width, height, reserve, gap, separation) {
    const barGap = separation === undefined ? gap : separation;
    let x = (screenWidth - width) / 2;
    let y = gap;
    if (edge === "bottom") y = screenHeight - reserve - gap - height;
    else if (edge === "left") { x = reserve + barGap; y = (screenHeight - height) / 2; }
    else if (edge === "right") { x = screenWidth - reserve - barGap - width; y = (screenHeight - height) / 2; }
    return {x: Math.max(gap, Math.min(screenWidth - width - gap, x)),
            y: Math.max(gap, Math.min(screenHeight - height - gap, y))};
}

function pickerSize(edge) {
    return vertical(edge) ? {width: 360, height: 620} : {width: 940, height: 196};
}
function gameFrameSize(edge, nativeSize) {
    return vertical(edge) ? {width: 420, height: 640} : nativeSize;
}
