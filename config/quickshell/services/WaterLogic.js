.pragma library

function dayKey(now) {
    const d = new Date(now)
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
}
function cleanMask(value) { return Number.isFinite(Number(value)) ? Math.trunc(Number(value)) & 255 : 0 }
function count(mask) {
    let total = 0
    for (let i = 0; i < 8; i++) total += (cleanMask(mask) >> i) & 1
    return total
}
function reminderDue(now, lastActivity, mask) {
    const hour = new Date(now).getHours()
    return hour >= 9 && hour < 21 && count(mask) < 8 && now - lastActivity >= 90 * 60 * 1000
}
