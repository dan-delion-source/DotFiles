// Upright modules for bottom/side bars; the existing island owns all panels.
import QtQuick
import QtQuick.Controls as QQC
import Quickshell
import "../services"
import "../theme"
import "../components"
import "./widgets"
import "BarGeometry.js" as Geometry

Item {
    id: root
    property string edge: SettingsService.barPosition
    property bool vertical: Geometry.vertical(root.edge)
    property real centreExtent: root.vertical ? root.spread ? columnClock.implicitHeight : Math.max(Theme.capsuleHeight * 1.8, (SettingsService.clockShowsSeconds ? 3 : 2) * (Theme.fontSizeRegular + 2) + 12) : ModuleService.restWidth
    property bool unified: SettingsService.barStyle === "island"
    property bool spread: SettingsService.barStyle === "spread"
    readonly property bool banded: root.spread && SettingsService.spreadBand
        && !(root.edge === "top" && SettingsService.islandAttached)
    property bool bare: !root.unified && !root.banded && SettingsService.barSides === "bare"
    readonly property real bandInset: root.banded ? Theme.bandEndPadding : 0
    readonly property real extent: root.vertical ? root.height : root.width
    readonly property real zoneRoom: Math.max(0, (root.extent - 2 * root.bandInset - root.centreExtent - 4 * Theme.capsuleSpacing) / 2)
    readonly property real beforeExtent: Math.min(before.naturalExtent, root.zoneRoom)
    readonly property real afterExtent: Math.min(after.naturalExtent, root.zoneRoom)
    readonly property real usedExtent: SettingsService.barFullWidth || root.spread
        ? root.extent : Math.min(root.extent, 2 * Math.max(root.beforeExtent, root.afterExtent) + root.centreExtent + 4 * Theme.capsuleSpacing)
    clip: true
    signal openRequested()

    Rectangle {
        objectName: "railBackground"
        x: root.vertical ? 0 : (root.width - root.usedExtent) / 2
        y: root.vertical ? (root.height - root.usedExtent) / 2 : 0
        width: root.vertical ? root.width : root.usedExtent
        height: root.vertical ? root.usedExtent : root.height
        visible: root.unified || root.banded
        radius: Math.min(width, height) / 2
        color: root.banded ? "#000000" : Theme.islandGround
        border.color: Theme.islandRim
        border.width: 1
    }

    Zone {
        id: before
        objectName: "leadingZone"
        entries: SettingsService.barItems("left")
        length: root.beforeExtent
        position: root.spread ? root.bandInset : (root.extent - root.centreExtent) / 2 - Theme.capsuleSpacing * 2 - length
    }
    Zone {
        id: after
        objectName: "trailingZone"
        entries: SettingsService.barItems("right")
        length: root.afterExtent
        position: root.spread ? root.extent - root.bandInset - length : (root.extent + root.centreExtent) / 2 + Theme.capsuleSpacing * 2
    }

    // Spread gives the side clock a taller column; other styles stay compact.
    // On the bottom the normal resting island occupies this central slot.
    Rectangle {
        objectName: "sideIslandButton"
        visible: root.vertical
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        width: root.width
        height: root.centreExtent
        radius: Theme.radiusLarge
        color: root.unified || root.banded ? "transparent" : Theme.islandGround
        border.width: root.unified || root.banded ? 0 : 1
        border.color: Theme.islandRim
        SystemClock { id: clock; precision: SystemClock.Seconds }
        StackedClock {
            id: columnClock
            objectName: "spreadColumnClock"
            anchors.fill: parent
            visible: root.spread
            date: clock.date
            format: SettingsService.clockFormat
            showSeconds: SettingsService.clockShowsSeconds
            showDate: SettingsService.clockShowsDate
        }
        Text {
            visible: !root.spread
            anchors.centerIn: parent
            width: Math.max(1, parent.width - 8)
            fontSizeMode: Text.Fit
            minimumPixelSize: 1
            text: Qt.formatDateTime(clock.date, SettingsService.clockFormat.replace(":", "\n") + (SettingsService.clockShowsSeconds ? "\nss" : ""))
            horizontalAlignment: Text.AlignHCenter
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sideClockFontSize
            font.weight: Font.DemiBold
            font.features: { "tnum": 1 }
            color: Theme.text
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openRequested()
        }
    }

    component Zone: Flickable {
        id: zone
        property var entries: []
        property real length: 0
        property real position: 0
        readonly property real naturalExtent: root.vertical ? content.implicitHeight : content.implicitWidth
        x: root.vertical ? (root.width - width) / 2 : zone.position
        y: root.vertical ? zone.position : 0
        width: root.vertical ? Math.max(1, root.width - (root.banded ? 8 : 0)) : zone.length
        height: root.vertical ? zone.length : root.height
        contentWidth: root.vertical ? width : content.implicitWidth
        contentHeight: root.vertical ? content.implicitHeight : height
        clip: true
        QQC.ScrollBar.vertical: QQC.ScrollBar { policy: root.vertical ? QQC.ScrollBar.AsNeeded : QQC.ScrollBar.AlwaysOff }
        QQC.ScrollBar.horizontal: QQC.ScrollBar { policy: root.vertical ? QQC.ScrollBar.AlwaysOff : QQC.ScrollBar.AsNeeded }
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: root.vertical ? Flickable.VerticalFlick : Flickable.HorizontalFlick
        BarZone {
            id: content
            vertical: root.vertical
            entries: zone.entries
            chromeless: root.unified || root.banded || root.bare
            overWallpaper: root.bare
            x: root.vertical ? (zone.width - width) / 2 : 0
        }
        WheelHandler {
            onWheel: event => {
                if (root.vertical)
                    zone.contentY = Math.max(0, Math.min(zone.contentHeight - zone.height, zone.contentY - event.angleDelta.y / 2));
                else
                    zone.contentX = Math.max(0, Math.min(zone.contentWidth - zone.width, zone.contentX - event.angleDelta.y / 2));
                event.accepted = true;
            }
        }
    }
}
