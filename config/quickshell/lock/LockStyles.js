.pragma library

var choices = [
    { id: "classic", label: "Classic" },
    { id: "mainframe", label: "Mainframe" }
];

function normalize(style) {
    return style === "mainframe" ? "mainframe" : "classic";
}

function motionFactor(motion) {
    return typeof motion === "number" && isFinite(motion)
        ? Math.max(0, Math.min(2, motion)) : 1;
}

function exitMs(style, motion) {
    return Math.round((normalize(style) === "mainframe" ? 1050 : 380) * motionFactor(motion));
}

// Boot login replaces its compositor. Give that boundary a deliberate pace;
// session locking keeps the shorter timings above.
function loginEnterMs(style, motion) {
    return Math.round((normalize(style) === "mainframe" ? 2200 : 1000) * motionFactor(motion));
}

function loginExitMs(style, motion) {
    return Math.round((normalize(style) === "mainframe" ? 1400 : 1000) * motionFactor(motion));
}

function segment(progress, from, to) {
    var value = Math.max(0, Math.min(1, (progress - from) / (to - from)));
    return 1 - Math.pow(1 - value, 3);
}
