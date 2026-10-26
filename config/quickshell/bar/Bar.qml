// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   B A R                                                                  │
// │   the bar · the island and its two sides, in three styles                │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import QtQuick.Effects
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland

import "../theme"
import "../services"
import "./widgets"
import "./modules"
import "./island"
import "./island/controls"
import "../components"
import "BarGeometry.js" as Geometry

// The island in the middle and the two sides (`SettingsService.barZone`), in
// one of three styles:
//
//   grouped   the sides sit against the island and move aside as it grows
//   spread    the sides sit at the screen edges and hold still
//   island    everything in one capsule; the band morphs into whatever the
//             island opens
//
// Every detail opens in the island. The window is full-screen and never
// resizes; the input mask covers the bar and the island, and a focus grab
// closes the island on any click outside it.
//
// ── ONE PER SCREEN, ONE LIVE ────────────────────────────────────────────────
//
// There is one of these on every screen and exactly one of them is `live`:
// the screen being worked on. The live bar opens panels, holds the keyboard
// and shows whatever arrives; the rest are the same bar with the island at
// rest, which is what the other screens were already drawing. So the island
// crossing screens is a flag changing hands — nothing is built, nothing is
// torn down, and what is under the pointer is always the one that answers it.
PanelWindow {
    id: root

    // Named for the blur behind it (`windowrules.lua`), which shows only
    // through a ground that is not solid.
    WlrLayershell.namespace: "danshell-bar"
    // What is drawn here takes the island's glass (`Theme.surfaceIn`).
    readonly property string edge: SettingsService.barPosition
    readonly property bool topEdge: root.edge === "top"
    readonly property bool vertical: Geometry.vertical(root.edge)
    readonly property real railThickness: Geometry.thickness(root.edge, Theme.capsuleHeight, SettingsService.sideBarWidth)
    readonly property real edgeReserve: Theme.barTopMargin + root.railThickness
    readonly property var popup: Geometry.popup(root.edge, root.width, root.height, island.width, island.height, root.edgeReserve, Theme.barTopMargin, root.vertical ? Theme.sidePopupGap : Theme.barTopMargin)
    readonly property bool glassy: true
    readonly property string groundStyle: Theme.surfaceStyle

    readonly property alias island: island

    // Whether this is the screen being worked on (`shell.qml`). Everything
    // below that touches state the whole shell shares is gated on it, because
    // every screen runs a copy of this file.
    required property bool live

    // Only the selected screen has a persistent bar; others host panels only.
    property bool barVisible: true

    // Whether this one is drawn at all. The surface is on every screen
    // either way and the reserve is `BarReserve`'s, which never moves, so a
    // desk set to one bar costs no window a re-tile when a hand crosses.
    readonly property bool painted: root.barVisible || (root.live && root.called)

    // The compositor's focus follows the pointer, so by the time anything here
    // is clicked this screen is already the live one. Said outright for the
    // case that is not a journey across the screen: a pointer warped onto the
    // bar, or a compositor not set to follow it.
    signal claimed()

    // Distance from the screen edge to the ends. Matches the compositor's
    // outer gap so the bar lines up with tiled windows.
    readonly property int edgeMargin: SettingsService.barSideMargin

    readonly property string style: SettingsService.barStyle
    readonly property bool spread: root.barVisible && root.style === "spread"
    readonly property bool unified: root.barVisible && root.style === "island"
    // The sides on the wallpaper, without capsules; not in one capsule, whose
    // band is the sides' ground.
    readonly property bool banded: root.spread && SettingsService.spreadBand && !SettingsService.barNotched
    readonly property int bandInset: root.banded ? Theme.bandEndPadding : 0
    readonly property bool bare: !root.unified && !root.banded && SettingsService.barSides === "bare"
    readonly property bool grouped: !root.spread && !root.unified

    // Stretch the band across the screen instead of fitting its contents.
    // Only the one-capsule style has a band.
    readonly property bool fullWidth: root.unified && SettingsService.barFullWidth

    readonly property bool holding: island.expanded

    // Maximum panel width. Spread, the sides stay put, so a panel gets the room
    // between them; otherwise the sides move aside and it gets the whole bar.
    readonly property int panelRoom: !root.topEdge
        ? Math.max(1, root.width - (root.vertical ? root.edgeReserve : 0) - 2 * Theme.barTopMargin)
        : root.spread
        ? root.width - 2 * (root.edgeMargin + root.bandInset
            + Math.max(leftZone.width, rightZone.width) + Theme.capsuleSpacing)
        : root.width - 2 * root.edgeMargin

    // Computed rather than read from `island.x`, which comes from an anchor
    // resolved during layout and would lag a frame behind the width.
    readonly property real islandLeft: (root.width - island.width) / 2
    readonly property real islandRight: root.islandLeft + island.width

    // ── ONE CAPSULE ─────────────────────────────────────────────────────────
    //
    // A band a capsule tall, with the sides at its ends and the island in the
    // middle. When the island shows anything beyond the clock, the band morphs
    // into it and the sides are clipped by its closing ends.

    // Inset of each side from the band's edge, clear of the curve.
    readonly property int hostedInset: 12

    // The same at both ends, so the clock stays centred on the screen.
    readonly property real hostedSlot: root.unified
        ? root.hostedInset + Math.max(leftZone.width, rightZone.width) + Theme.capsuleSpacing * 2
        : 0

    // The island's width inside the band, animated on the island's clock so
    // the band widens with it. An OSD is wider than the clock and pushes the
    // sides out rather than overlapping them.
    property real restWidth: island.state.layer === island.state.layerOsd
        ? Math.max(ModuleService.restWidth, island.size.width)
        : ModuleService.restWidth

    Behavior on restWidth {
        NumberAnimation { duration: Theme.durationMorph; easing.type: Theme.easing }
    }

    // The band at rest: the island's rest width plus a slot for each side.
    readonly property real bodyWidth: {
        if (!root.unified)
            return island.width
        if (root.fullWidth)
            return root.width - 2 * root.edgeMargin
        return root.restWidth + 2 * root.hostedSlot
    }

    readonly property real bandRow: Theme.capsuleHeight + island.notchPad

    // The island is showing more than the clock: a panel, a detail, the
    // glance or a notification. An OSD fits in the band and does not count.
    // In zen too, where the sides are away and the band is only the island.
    readonly property bool islandTaken: island.expanded
        || island.state.layer === island.state.layerSummary
        || island.state.layer === island.state.layerNotification
        || root.zen
    readonly property real bodyX: root.fullWidth
        ? root.edgeMargin : (root.width - root.bodyWidth) / 2

    // 0 at rest, 1 once the island has taken over the band. Animated on the
    // island's clock and curve so the two land together.
    property real bandInto: root.unified && root.islandTaken ? 1 : 0

    Behavior on bandInto {
        enabled: island.animated
        NumberAnimation { duration: Theme.durationMorph; easing.type: Theme.easing }
    }

    // Interpolates from the rest width to the island's animated width as
    // `bandInto` goes from 0 to 1. Both run on the same curve, so this is one
    // morph with no clock of its own. The max() stops a spring curve's
    // overshoot from making the band narrower than the island.
    readonly property real bandWidth: root.bandInto === 0 && !root.islandTaken
        ? root.bodyWidth
        : island.width + (root.bodyWidth - root.restWidth) * Math.max(0, 1 - root.bandInto)
    readonly property real bandX: (root.width - root.bandWidth) / 2

    // Attached (notch mode), only the island reaches the screen edge; the
    // sides stay capsules, centred on `laneY`.
    readonly property int islandTopMargin: root.topEdge && SettingsService.islandAttached ? 0 : Theme.barTopMargin

    // How far the glass's light from the top reaches down the notch
    // (`GlassSheen`), for the fillets that carry it on.
    readonly property real notchSheen: Theme.glass && !island.paper ? Theme.glassSheenDepth : 0

    // The line everything on the bar is centred on. Attached, the island
    // reaches the screen edge, so its centre is half a margin higher and the
    // sides move up to match.
    readonly property real laneY: SettingsService.islandAttached
        ? Theme.barTopMargin / 2 : Theme.barTopMargin

    readonly property int collapsedHeight: Theme.barBand

    // Grouped, the sides make room for a module detail but hide for a panel.
    // In one capsule they hide whenever the island takes the band.
    readonly property bool sidesAway: root.unified
        ? root.islandTaken
        : island.expanded && root.grouped && island.state.openPanel !== "module"

    anchors {
        top: true
        bottom: true
        left: true
        right: true
    }

    // ── SURFACE ─────────────────────────────────────────────────────────────
    //
    // The layer surface is full-screen and never resizes: resizing it on every
    // animation frame makes the bar jitter, because the compositor applies the
    // new size a frame before or after the matching buffer. Input is handled by
    // the mask, which is cheap to change per frame.
    implicitHeight: root.screen.height

    // Input region: the bar's band, plus the island's shape (the band's, in
    // one capsule) with 12 px below it so the bottom edge still counts. The
    // whole screen only while the control centre is being arranged, since
    // blocks are dragged out of the tray card, which moves. Outside clicks are
    // left to the focus grab, so windows under an open panel stay usable.
    readonly property real shapeLeft: root.unified
        ? Math.min(root.bandX, root.islandLeft) : root.islandLeft
    readonly property real shapeRight: root.unified
        ? Math.max(root.bandX + root.bandWidth, root.islandRight) : root.islandRight
    readonly property bool wholeScreen: root.holding && ControlsService.editing

    readonly property bool inert: !root.painted || root.away

    // Zen (`barHidden`): the bar waits above the screen and the island comes
    // down only for what it has to show — a panel, a notification, a
    // transient — with the sides left up there.
    readonly property bool zen: SettingsService.barHidden || !root.barVisible
    readonly property bool called: island.state.layer !== island.state.layerModules
        && island.state.layer !== island.state.layerSummary
    readonly property bool away: root.zen && !root.called

    mask: Region {
        Region {
            x: root.wholeScreen ? 0 : root.edge === "right" ? root.width - root.edgeReserve - 8 : 0
            y: root.wholeScreen ? 0 : root.edge === "bottom" ? root.height - root.edgeReserve - 8 : 0
            width: root.inert || (root.zen && !root.wholeScreen) ? 0 : root.wholeScreen ? root.width
                : root.vertical ? root.edgeReserve + 8 : root.width
            height: root.inert ? 0 : root.wholeScreen ? root.height
                : root.vertical ? root.height : root.edgeReserve + 8
        }
        Region {
            x: island.x
            y: island.y
            width: root.inert || !island.visible ? 0 : island.width
            height: root.inert || !island.visible ? 0 : island.height
        }
    }

    // The reserve is `BarReserve.qml`'s, one strip per screen that outlives
    // every bar, so a window holds still while the island changes screens.
    // Ignoring zones is what keeps the bar against the edge: a surface that
    // reserves nothing is pushed below whatever else reserved.
    exclusionMode: ExclusionMode.Ignore
    exclusiveZone: 0
    color: "transparent"

    // ── FOCUS ───────────────────────────────────────────────────────────────
    //
    // On-demand keyboard focus plus a Hyprland focus grab while the island is
    // open. The grab keeps the keyboard here when the pointer crosses a window
    // (with `follow_mouse`, on-demand focus alone loses it), and a click on any
    // other surface clears it, which closes the island. The compositor
    // restores focus when the grab ends. Both stand down while the capture
    // surface is up, so an open panel waits under it instead of closing.
    readonly property bool holdsKeyboard: root.live && island.expanded
        && !CaptureService.active

    WlrLayershell.keyboardFocus: root.holdsKeyboard
        ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    HyprlandFocusGrab {
        active: root.holdsKeyboard
        windows: [root]
        onCleared: root.dismiss()
    }

    HoverHandler {
        onHoveredChanged: if (hovered) root.claimed()
    }

    Connections {
        target: SettingsService
        function onBarPositionChanged(): void {
            root.dismiss()
            if (root.live && ControlsService.editing) ControlsService.edit(false)
        }
    }

    // ── OPENING A DETAIL ────────────────────────────────────────────────────
    //
    // Every activation on the bar comes through here
    // (`ModuleService.activate`). Clicking the open module again closes it; any
    // other replaces it.
    function activate(id: string): void {
        if (ModuleService.openId === id) {
            root.dismiss()
            return
        }

        // Always in the island, whatever the style or screen.
        ModuleService.openHost = "island"
        ModuleService.openId = id
        island.open("module")
    }

    function dismiss(): void {
        if (island.expanded)
            island.close()
        ModuleService.close()
    }

    // Every bar hears these; only the live one answers, since the panel opens
    // in its island.
    Connections {
        target: ModuleService
        enabled: root.live

        function onActivationRequested(id: string): void {
            root.activate(id)
        }

        // Bar buttons for panels (launcher, overview) toggle them.
        function onPanelToggled(panel: string): void {
            island.toggle(panel)
        }

        // The service closed the detail, e.g. the player went away.
        function onOpenIdChanged(): void {
            if (ModuleService.openId === "" && island.state.openPanel === "module")
                island.close()
        }
    }

    // Lets a bar button stay lit while its panel is open. One writer: the
    // live bar, since two bars binding the same property is a conflict.
    Binding {
        target: ModuleService
        property: "shownPanel"
        value: island.state.openPanel
        when: root.live
    }

    Connections {
        target: island.state

        // The island left the detail (Escape, a click outside, another panel).
        function onOpenPanelChanged(): void {
            if (island.state.openPanel !== "module" && ModuleService.openHost === "island")
                ModuleService.close()
        }
    }

    // Clicks on the bar outside the open island close it. The bar is inside
    // the focus grab, so the grab never sees them.
    MouseArea {
        anchors.fill: parent
        enabled: root.holding
        onClicked: root.dismiss()
    }

    // ── THE FACE ────────────────────────────────────────────────────────────
    //
    // Everything this bar draws. The surface stays on every screen whatever
    // `barEverywhere` says, so the reserve never moves and no window is ever
    // re-tiled by a hand crossing; what the setting decides is only whether
    // this is painted. Nothing is built or torn down either way.
    Item {
        id: face

        width: parent.width
        height: parent.height
        y: root.topEdge && root.away ? -2 * root.collapsedHeight : 0
        visible: root.painted || face.opacity > 0
        opacity: root.painted ? 1 : 0

        Behavior on opacity {
            NumberAnimation { duration: Theme.durationFast; easing.type: Theme.easing }
        }

        Behavior on y {
            NumberAnimation { duration: Theme.durationMedium; easing.type: Theme.easing }
        }

        // ── SHADOW ──────────────────────────────────────────────────────────────
        //
        // The window shadow's numbers, on its own setting (`barShadow`). The
        // band, the island and the notch fillets touch, so they share one
        // flattened layer; separate shadows would draw a seam where they
        // overlap. The side capsules cast their own (`BarZone`).
        //
        // Cast from a copy of the shapes: layering the real bar would re-blur the
        // full-screen surface every time the clock or the spectrum repaints.
        //
        // The copy is grown by `Theme.shadowBarSpread` and blurred. MultiEffect's
        // `shadowEnabled` would also draw the source, showing the enlarged copy as
        // a black rim. `layer.effect` rather than a hidden `source` item, which
        // does not work inside a Repeater.
        Loader {
            anchors.fill: parent
            active: root.topEdge && SettingsService.barShadow
            sourceComponent: shadowBody
        }

        Component {
            id: shadowBody

            // Under a ground that lets the screen through, the shapes are cut
            // out of their shadow, so it falls outside them and does not show
            // through.
            Item {
                layer.enabled: !Theme.solid
                layer.effect: MultiEffect {
                    maskEnabled: true
                    maskInverted: true
                    maskSource: cutout
                    maskThresholdMin: 0.5
                    maskSpreadAtMin: 1
                }

                Item {
                    id: cutout

                    anchors.fill: parent
                    visible: false
                    layer.enabled: !Theme.solid

                    Rectangle {
                        x: band.x
                        y: SettingsService.islandAttached ? 0 : band.y
                        width: band.width
                        height: band.y + band.height - y
                        radius: band.radius
                        topLeftRadius: band.topLeftRadius
                        topRightRadius: band.topRightRadius
                        // Not `visible`: inside the hidden source it reads false
                        // and the band is left out of the mask.
                        opacity: root.unified ? 1 : 0
                    }

                    // Attached, the shadow runs up to the screen's edge, so the
                    // cut does too while the island slides up into the notch.
                    Rectangle {
                        x: root.islandLeft
                        y: SettingsService.islandAttached ? 0 : island.y
                        width: island.width
                        height: island.y + island.height - y
                        radius: island.radius
                        topLeftRadius: SettingsService.islandAttached ? 0 : island.topLeftRadius
                        topRightRadius: SettingsService.islandAttached ? 0 : island.topRightRadius
                    }

                    Repeater {
                        model: [notchLeft, notchRight]

                        NotchFillet {
                            required property var modelData

                            x: modelData.x
                            y: modelData.y
                            width: modelData.width
                            height: modelData.height
                            opacity: modelData.visible ? 1 : 0
                            mirrored: modelData.mirrored
                            color: "black"
                        }
                    }
                }

                Item {
                    id: caster

                    // Attached, the layer runs above the screen by the blur's reach and
                    // the shapes run up into it, so the blur reads the notch as going on
                    // past the edge and the shadow keeps its weight up to the top.
                    anchors.fill: parent
                    anchors.topMargin: -caster.pad
                    opacity: Theme.shadowOpacity

                    layer.enabled: true
                    layer.effect: MultiEffect {
                        blurEnabled: true
                        blur: 1
                        blurMax: Theme.shadowBarRange - Theme.shadowBarSpread
                    }

                    readonly property int spread: Theme.shadowBarSpread
                    readonly property int pad: SettingsService.islandAttached ? Theme.shadowBarRange : 0

                    Rectangle {
                        x: band.x - caster.spread
                        y: band.y - caster.spread
                        width: band.width + 2 * caster.spread
                        height: band.height + 2 * caster.spread + caster.pad
                        radius: band.radius + caster.spread
                        topLeftRadius: band.topLeftRadius > 0 ? band.topLeftRadius + caster.spread : 0
                        topRightRadius: band.topRightRadius > 0 ? band.topRightRadius + caster.spread : 0
                        visible: body.visible
                        color: Theme.shadowColor
                    }

                    Rectangle {
                        x: root.islandLeft - caster.spread
                        y: island.y - caster.spread
                        width: island.width + 2 * caster.spread
                        height: island.height + 2 * caster.spread + caster.pad
                        radius: island.radius + caster.spread
                        topLeftRadius: island.topLeftRadius > 0 ? island.topLeftRadius + caster.spread : 0
                        topRightRadius: island.topRightRadius > 0 ? island.topRightRadius + caster.spread : 0
                        color: Theme.shadowColor
                    }

                    // The fillets grown by the spread as the rectangles are: the same
                    // centre, a radius short by the spread, and a strip for the top
                    // edge moved up by it. Past the tip the strip runs on along the
                    // edge and fades out, or the shadow down the curve stops square
                    // where the curve meets the edge.
                    Repeater {
                        model: [notchLeft, notchRight]

                        Item {
                            required property var modelData

                            x: modelData.x
                            y: caster.pad + modelData.y
                            width: modelData.width
                            height: modelData.height
                            visible: modelData.visible
                            opacity: modelData.opacity

                            // Solid only: along the edge of the screen a
                            // see-through notch would show it as a stain.
                            Rectangle {
                                y: -caster.pad
                                visible: Theme.solid
                                width: parent.width
                                height: caster.pad + caster.spread
                                color: Theme.shadowColor
                            }

                            Rectangle {
                                id: tail

                                readonly property bool mirrored: parent.modelData.mirrored

                                x: mirrored ? -width : parent.width
                                y: -caster.pad
                                visible: Theme.solid
                                width: parent.width * 2
                                height: caster.pad + caster.spread
                                gradient: Gradient {
                                    orientation: Gradient.Horizontal
                                    GradientStop { position: 0; color: tail.mirrored ? "transparent" : Theme.shadowColor }
                                    GradientStop { position: 1; color: tail.mirrored ? Theme.shadowColor : "transparent" }
                                }
                            }

                            NotchFillet {
                                x: parent.modelData.mirrored ? 0 : caster.spread
                                y: caster.spread
                                width: Math.max(0, parent.width - caster.spread)
                                height: Math.max(0, parent.height - caster.spread)
                                mirrored: parent.modelData.mirrored
                                color: Theme.shadowColor
                            }
                        }
                    }

                }
            }
        }

        // ── BAND ────────────────────────────────────────────────────────────────
        //
        // Two shapes of the same black: the band, and the island on top of it.
        // Neither has an outline, which would draw the seam between them.
        Item {
            id: body

            anchors.fill: parent
            visible: root.topEdge && root.unified

            // Grows with the island; at rest both share height and radius.
            Rectangle {
                id: band

                x: root.bandX
                y: root.islandTopMargin
                width: root.bandWidth
                height: Math.max(root.bandRow, island.height)
                radius: island.radius
                topLeftRadius: SettingsService.islandAttached ? 0 : band.radius
                topRightRadius: SettingsService.islandAttached ? 0 : band.radius
                color: island.surfaceColor

                Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                // The band is the ground here, so it carries the glass.
                GlassSheen {
                    shape: band
                    visible: Theme.glass && !island.paper
                    edges: !SettingsService.islandAttached
                }

                // Clicking the band opens the island. The sides sit above it and
                // take their own clicks.
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: island.open("controls")
                }
            }
        }

        Loader {
            active: !root.topEdge && root.barVisible && !root.zen
            x: root.edge === "right" ? root.width - root.edgeReserve : root.vertical ? Theme.barTopMargin : root.edgeMargin
            y: root.edge === "bottom" ? root.height - root.edgeReserve : root.edgeMargin
            width: root.vertical ? root.railThickness : root.width - 2 * root.edgeMargin
            height: root.vertical ? root.height - 2 * root.edgeMargin : Theme.capsuleHeight
            sourceComponent: EdgeRail {
                anchors.fill: parent
                onOpenRequested: island.toggle("controls")
            }
        }

        Rectangle {
            objectName: "spreadBackgroundBand"
            visible: root.topEdge && root.banded && !root.zen
            x: root.edgeMargin
            y: Theme.barTopMargin
            width: Math.max(1, root.width - 2 * root.edgeMargin)
            height: Theme.capsuleHeight
            radius: Math.min(width, height) / 2
            color: "#000000"
            MouseArea { anchors.fill: parent; onClicked: island.toggle("controls") }
        }

        DynamicIsland {
            id: island
            blackBand: root.banded

            active: root.live
            hosted: root.topEdge && root.unified
            attached: root.topEdge && SettingsService.islandAttached
            maximumHeight: Math.max(1, root.height - (root.edge === "bottom" ? root.edgeReserve : 0) - 2 * Theme.barTopMargin)
            roomForPanel: root.panelRoom
            x: root.topEdge || root.edge === "bottom" ? (parent.width - width) / 2 : root.popup.x
            y: root.topEdge ? root.islandTopMargin : root.edge === "bottom" && island.state.layer === island.state.layerModules
                ? root.height - Theme.barTopMargin - height : root.popup.y
            visible: !root.vertical || island.state.layer !== island.state.layerModules

            Behavior on y {
                enabled: root.topEdge && island.animated
                NumberAnimation { duration: Theme.durationMedium; easing.type: Theme.easing }
            }
        }

        // The island's hairline, drawn round the band once it takes the island's
        // shape. Above both, since the opaque island covers the band's own edge.
        // None at rest and none in paper mode.
        Rectangle {
            id: outline

            x: band.x
            y: band.y
            width: band.width
            height: band.height
            radius: band.radius
            topLeftRadius: band.topLeftRadius
            topRightRadius: band.topRightRadius
            visible: root.topEdge && root.unified && !island.paper && !SettingsService.islandAttached
            color: "transparent"
            border.width: 1
            border.color: root.islandTaken ? Theme.islandRim : "transparent"

            Behavior on border.color { ColorAnimation { duration: Theme.durationMedium } }
        }

        // The control centre's tray card while its grid is being arranged. On this
        // surface so blocks can be dragged from it onto the island; it fills the
        // surface and starts under the island.
        Item {
            id: overlay

            anchors.fill: parent
            z: 3

            // Right under the island, the grid's size, then the card of
            // blocks.
            Loader {
                id: arranging

                x: (parent.width - width) / 2
                y: root.topEdge ? root.islandTopMargin + island.height + Theme.surfaceGutter : Theme.surfaceGutter
                active: root.live && ControlsService.editing
                sourceComponent: GridSize {}
            }

            Loader {
                anchors.fill: parent
                active: root.live && ControlsService.editing
                sourceComponent: ControlsTray {
                    host: overlay
                    homeTop: arranging.y + (arranging.item ? arranging.item.height : 0)
                        + Theme.surfaceGutter
                }
            }
        }

        // Notch fillets flaring from the island's edges out to the screen edge.
        // In one capsule they follow whichever edge is further out, the band's or
        // the island's, since a spring curve can push the island past the band.
        NotchFillet {
            id: notchLeft

            x: (root.unified ? Math.min(root.bandX, root.islandLeft) : root.islandLeft) - width
            anchors.top: parent.top
            visible: root.topEdge && SettingsService.islandAttached
            mirrored: true
            color: island.surfaceColor
            sheenReach: root.notchSheen
        }

        NotchFillet {
            id: notchRight

            x: root.unified ? Math.max(root.bandX + root.bandWidth, root.islandRight) : root.islandRight
            anchors.top: parent.top
            visible: root.topEdge && SettingsService.islandAttached
            color: island.surfaceColor
            sheenReach: root.notchSheen
        }

        // On glass, attached, the island and its fillets are one pane: the
        // light from the top runs on into the fillets, and the thick edge
        // follows the outline below rather than the island's own rectangle.
        Repeater {
            model: root.topEdge && SettingsService.islandAttached && Theme.glass && !island.paper
                ? [[1, 1], [2, 0.6], [3, 0.35], [4, 0.15]] : []

            NotchOutline {
                required property var modelData

                inset: modelData[0]
                shapeLeft: root.shapeLeft
                shapeRight: root.shapeRight
                shapeHeight: root.unified ? band.height : island.height
                radius: island.radius
                color: Qt.rgba(1, 1, 1, Theme.glassEdge * modelData[1])
            }
        }

        // Attached, the hairline runs down the fillets and round the shape, and
        // not along the screen edge. In one capsule only while the island has
        // the band, as `outline` above.
        NotchOutline {
            visible: root.topEdge && SettingsService.islandAttached && !island.paper
            shapeLeft: root.shapeLeft
            shapeRight: root.shapeRight
            shapeHeight: root.unified ? band.height : island.height
            radius: island.radius
            color: !root.unified || root.islandTaken ? Theme.islandRim : "transparent"

            Behavior on color { ColorAnimation { duration: Theme.durationMedium } }
        }

        component BareShadow: MultiEffect {
            shadowEnabled: true
            blurMax: Theme.barShadowReach
            shadowBlur: 1
            shadowVerticalOffset: 1
            shadowColor: Theme.barShadow
        }

        // ── SIDES ───────────────────────────────────────────────────────────────
        //
        // Grouped, the sides are anchored to the island's animated edges, so they
        // move aside on its clock with nothing else to animate. Spread, they stay
        // in the corners. In one capsule they are the band's ends; while it morphs
        // they are clipped by it and fade out faster than it closes.
        Item {
            id: sides

            readonly property bool cropped: root.unified && root.bandInto > 0

            x: sides.cropped ? band.x : 0
            y: 0
            width: sides.cropped ? band.width : root.width
            height: root.height
            clip: sides.cropped
            opacity: root.zen ? 0 : 1
            visible: root.topEdge && opacity > 0

            Behavior on opacity {
                NumberAnimation { duration: Theme.durationFast; easing.type: Theme.easing }
            }

            // On the wallpaper, the sides are cast twice: the shadow's own
            // shadow is what makes a thin dark edge dense enough to hold white
            // off a light picture, which one blurred copy of a small glyph is
            // not.
            layer.enabled: root.bare
            layer.effect: BareShadow {}

            Loader {
                id: leftZone
                active: root.topEdge
                sourceComponent: BarZone {
                    entries: SettingsService.barItems("left")
                    chromeless: root.unified || root.banded || root.bare
                    overWallpaper: root.bare
                }

                layer.enabled: root.bare
                layer.effect: BareShadow {}
                x: (root.unified ? root.bodyX + root.hostedInset
                    : root.spread ? root.edgeMargin + root.bandInset
                    : root.islandLeft - Theme.capsuleSpacing - leftZone.width) - sides.x
                y: root.laneY
                opacity: root.sidesAway ? 0 : 1
                visible: opacity > 0

                Behavior on opacity {
                    NumberAnimation {
                        duration: root.unified && root.sidesAway ? Theme.durationFast : Theme.durationMedium
                        easing.type: Theme.easing
                    }
                }
            }

            Loader {
                id: rightZone
                active: root.topEdge
                sourceComponent: BarZone {
                    entries: SettingsService.barItems("right")
                    chromeless: root.unified || root.banded || root.bare
                    overWallpaper: root.bare
                }

                layer.enabled: root.bare
                layer.effect: BareShadow {}
                x: (root.unified ? root.bodyX + root.bodyWidth - root.hostedInset - rightZone.width
                    : root.spread ? root.width - root.edgeMargin - root.bandInset - rightZone.width
                    : root.islandRight + Theme.capsuleSpacing) - sides.x
                y: root.laneY
                opacity: root.sidesAway ? 0 : 1
                visible: opacity > 0

                Behavior on opacity {
                    NumberAnimation {
                        duration: root.unified && root.sidesAway ? Theme.durationFast : Theme.durationMedium
                        easing.type: Theme.easing
                    }
                }
            }
        }
    }
}
