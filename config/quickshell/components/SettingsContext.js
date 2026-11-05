.pragma library

// Shared controls adopt this presentation only inside the Settings window.
function contains(item) {
    for (let node = item.parent; node; node = node.parent) {
        if (node.settingsPresentation === true)
            return true
    }
    return false
}
