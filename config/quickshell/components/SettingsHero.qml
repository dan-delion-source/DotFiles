// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S E T T I N G S   H E R O                                              │
// │   settings page heading                                                  │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import QtQuick.Layouts

import "../theme"

// Settings page header: mark and name, left-aligned, a step larger than the
// group headings.
RowLayout {
    id: root

    property string icon: ""
    property string title: ""
    property string subtitle: ""

    spacing: 12

    Rectangle {
        Layout.preferredWidth: 38
        Layout.preferredHeight: 38
        radius: 9
        color: Theme.islandSurface
        border.color: Theme.islandBorder
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: root.icon
            font.family: Theme.fontMono
            font.pixelSize: 17
            color: Theme.accent
        }
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Text {
            Layout.fillWidth: true
            text: root.title
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeLarge
            font.weight: Font.DemiBold
            color: Theme.text
        }

        Text {
            Layout.fillWidth: true
            visible: root.subtitle !== ""
            text: root.subtitle
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeSmall
            color: Theme.textMuted
            elide: Text.ElideRight
        }
    }
}
