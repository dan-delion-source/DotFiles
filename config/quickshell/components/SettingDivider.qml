// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S E T T I N G   D I V I D E R                                          │
// │   settings · the hairline between two rows                               │
// │                                                                          │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick

import Quickshell
import "../theme"

// Drawn by the lower of two rows in a `SettingGroup`, and only when there is
// a row above it: the first visible row sits at the top of the card.
Rectangle {
    visible: parent !== null && parent.y > 0
    width: parent ? parent.width : 0
    height: 1
    color: Theme.borderIn(QsWindow.window)
}
