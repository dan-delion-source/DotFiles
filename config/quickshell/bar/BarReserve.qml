// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   B A R   R E S E R V E                                                  │
// │   the space the bar keeps · held by the screen, not by the bar           │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import Quickshell
import Quickshell.Wayland

import "../theme"
import "../services"
import "BarGeometry.js" as Geometry

// One strip per screen, a pixel tall and painting nothing, whose only job is
// the exclusive zone. The bars reserve nothing themselves, so a bar replaced
// by another kind never lets the space go: tiled windows hold still while the
// island changes screens.
PanelWindow {
    id: root

    anchors {
        top: SettingsService.barPosition !== "bottom"
        bottom: SettingsService.barPosition !== "top"
        left: SettingsService.barPosition !== "right"
        right: SettingsService.barPosition !== "left"
    }

    implicitHeight: 1
    implicitWidth: 1
    color: "transparent"
    // Nothing in zen, so the windows take the band.
    exclusiveZone: SettingsService.barHidden ? 0
        : Theme.barTopMargin + Geometry.thickness(SettingsService.barPosition, Theme.capsuleHeight, SettingsService.sideBarWidth)

    // Under everything, and deaf.
    WlrLayershell.layer: WlrLayer.Background
    mask: Region {}
}
