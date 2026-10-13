// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   I S L A N D   S U M M A R Y                                            │
// │   hover summary · the time and what is playing                           │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import Quickshell
import Quickshell.Widgets

import "../../theme"
import "../../services"

// The glance, in two faces. With a player: the cover large, the track and its
// three controls, and the time large at the far end with the day and the date
// under it. Without one: the time large with the weather on a small line under
// it, where the weather is already asked for, and at the far end five days of
// the week with today in the middle. The controls are the only things on it to
// press; a click anywhere else is the control centre.
Item {
    id: root

    SystemClock {
        id: clock
        precision: SystemClock.Minutes
    }

    Component.onCompleted: MediaService.subscribe()
    Component.onDestruction: MediaService.release()

    readonly property bool media: MediaService.available
    readonly property var locale: Qt.locale(SettingsService.language)

    readonly property int margin: 19

    // ── WITH A PLAYER ───────────────────────────────────────────────────────

    Item {
        anchors.fill: parent
        visible: root.media

        ClippingRectangle {
            id: cover

            x: root.margin
            anchors.verticalCenter: parent.verticalCenter
            width: parent.height - 2 * root.margin
            height: width
            radius: width * Theme.pictureCorner
            // Only under the placeholder: a player that sends its own logo
            // rather than a cover sends it on transparency, and a box behind
            // it reads as part of the picture.
            color: art.visible ? "transparent" : Theme.surfaceHoverIn(QsWindow.window)

            Image {
                id: art

                anchors.fill: parent
                source: MediaService.artUrl
                visible: source != "" && status === Image.Ready
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                sourceSize.width: 288
                sourceSize.height: 288
            }

            Text {
                anchors.centerIn: parent
                visible: !art.visible
                text: "󰎇"
                font.family: Theme.fontMono
                font.pixelSize: 34
                color: Theme.indicator
            }
        }

        Column {
            anchors.left: cover.right
            anchors.leftMargin: 16
            anchors.right: time.left
            anchors.rightMargin: 16
            anchors.verticalCenter: cover.verticalCenter
            spacing: 4

            Text {
                width: parent.width
                text: MediaService.title || MediaService.identity
                elide: Text.ElideRight
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeMedium
                font.weight: Font.Bold
                color: Theme.text
            }

            Text {
                width: parent.width
                visible: text !== ""
                text: MediaService.artist
                elide: Text.ElideRight
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeRegular
                color: Theme.textMuted
            }

            Item {
                width: 1
                height: 10
            }

            Row {
                spacing: 8

                Control {
                    glyph: "󰒮"
                    size: 17
                    live: MediaService.canPrevious
                    onPressed: MediaService.previous()
                }

                Control {
                    glyph: MediaService.playing ? "󰏤" : "󰐊"
                    size: 22
                    live: MediaService.canToggle
                    onPressed: MediaService.toggle()
                }

                Control {
                    glyph: "󰒭"
                    size: 17
                    live: MediaService.canNext
                    onPressed: MediaService.next()
                }
            }
        }

        Clock {
            id: time

            anchors.right: parent.right
            anchors.rightMargin: root.margin + 4
            anchors.verticalCenter: cover.verticalCenter
            align: Text.AlignRight
            timeSize: 62
        }
    }

    // ── WITHOUT ONE ─────────────────────────────────────────────────────────

    Item {
        anchors.fill: parent
        visible: !root.media

        Column {
            x: root.margin + 4
            anchors.verticalCenter: parent.verticalCenter
            spacing: -4

            Text {
                text: Qt.formatDateTime(clock.date, SettingsService.clockFormat)
                font.family: Theme.fontFamily
                font.pixelSize: 62
                font.weight: Font.Black
                color: Theme.text
            }

            Row {
                visible: ModuleService.summaryWeather
                spacing: 6

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: WeatherService.glyph
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSizeRegular
                    color: Theme.textMuted
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: [`${WeatherService.temperature}°`, WeatherService.place ?? ""]
                        .filter(part => part !== "").join("  ·  ")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSmall + 1
                    font.weight: Font.DemiBold
                    color: Theme.textMuted
                }
            }
        }

        // Five days, today in the middle: its short name over its date, lit;
        // the others a letter over a date, dim.
        Row {
            anchors.right: parent.right
            anchors.rightMargin: root.margin + 2
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Repeater {
                model: 5

                Column {
                    id: day

                    required property int index

                    readonly property date date: {
                        const shown = new Date(clock.date)
                        shown.setDate(shown.getDate() + day.index - 2)
                        return shown
                    }
                    readonly property bool today: day.index === 2
                    readonly property string name: root.locale.toString(day.date, "ddd")
                        .replace(".", "").toUpperCase()

                    width: 30
                    spacing: 3

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: day.today ? day.name : day.name.charAt(0)
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeLabel
                        font.weight: Font.Bold
                        color: day.today ? Theme.accent : Theme.textMuted
                        opacity: day.today ? 1 : 0.7
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: day.date.getDate()
                        font.family: Theme.fontFamily
                        font.pixelSize: day.today ? 19 : 15
                        font.weight: day.today ? Font.Black : Font.DemiBold
                        color: day.today ? Theme.text : Theme.textMuted
                        opacity: day.today ? 1 : 0.55
                    }
                }
            }
        }
    }

    // ── PIECES ──────────────────────────────────────────────────────────────

    // The time in the heaviest weight, the day and the date under it in
    // capitals.
    component Clock: Column {
        id: face

        property int align: Text.AlignRight
        property int timeSize: 62

        spacing: -6

        Text {
            anchors.right: face.align === Text.AlignRight ? parent.right : undefined
            text: Qt.formatDateTime(clock.date, SettingsService.clockFormat)
            font.family: Theme.fontFamily
            font.pixelSize: face.timeSize
            font.weight: Font.Black
            color: Theme.text
        }

        Text {
            anchors.right: face.align === Text.AlignRight ? parent.right : undefined
            text: root.locale.toString(clock.date, "dddd").toUpperCase()
            font.family: Theme.fontFamily
            font.pixelSize: 20
            font.weight: Font.Black
            color: Theme.text
        }

        Text {
            anchors.right: face.align === Text.AlignRight ? parent.right : undefined
            text: root.locale.toString(clock.date, "d MMMM").toUpperCase()
            font.family: Theme.fontFamily
            font.pixelSize: 15
            font.weight: Font.Black
            color: Theme.textMuted
        }
    }

    // A player control: its glyph, lit under the pointer.
    component Control: Item {
        id: control

        property string glyph: ""
        property int size: 20
        property bool live: true
        signal pressed()

        width: control.size + 16
        height: width
        opacity: control.live ? 1 : 0.35

        Rectangle {
            anchors.fill: parent
            radius: width / 2
            color: Theme.surfaceHoverIn(QsWindow.window)
            opacity: mouse.containsMouse && control.live ? 1 : 0

            Behavior on opacity { NumberAnimation { duration: Theme.durationFast } }
        }

        Text {
            anchors.centerIn: parent
            text: control.glyph
            font.family: Theme.fontMono
            font.pixelSize: control.size
            color: Theme.text
        }

        MouseArea {
            id: mouse

            anchors.fill: parent
            enabled: control.live
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: control.pressed()
        }
    }
}
