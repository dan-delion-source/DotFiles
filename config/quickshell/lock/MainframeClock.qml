import QtQuick

// Five-by-seven phosphor cells, authored as geometry rather than a font image.
Item {
    id: root
    property string time: "09:41"
    property color ink: "#b6e6ce"
    readonly property var glyphs: ({
        "0": ["01110", "11011", "11011", "11011", "11011", "11011", "01110"],
        "1": ["00110", "01110", "00110", "00110", "00110", "00110", "01111"],
        "2": ["01110", "11011", "00011", "00110", "01100", "11000", "11111"],
        "3": ["11110", "00011", "00011", "01110", "00011", "00011", "11110"],
        "4": ["00011", "00111", "01111", "11011", "11111", "00011", "00011"],
        "5": ["11111", "11000", "11000", "11110", "00011", "00011", "11110"],
        "6": ["01110", "11000", "11000", "11110", "11011", "11011", "01110"],
        "7": ["11111", "00011", "00110", "00110", "01100", "01100", "01100"],
        "8": ["01110", "11011", "11011", "01110", "11011", "11011", "01110"],
        "9": ["01110", "11011", "11011", "01111", "00011", "00011", "01110"],
        ":": ["00000", "00110", "00110", "00000", "00110", "00110", "00000"]
    })
    implicitWidth: 434
    implicitHeight: 98

    Repeater {
        model: 5
        Item {
            id: digit
            required property int index
            readonly property var rows: root.glyphs[root.time.charAt(index)] ?? root.glyphs["0"]
            x: index * 88
            width: 70
            height: 98
            Repeater {
                model: 35
                Rectangle {
                    required property int index
                    x: (index % 5) * 14
                    y: Math.floor(index / 5) * 14
                    width: 11
                    height: 10
                    visible: digit.rows[Math.floor(index / 5)].charAt(index % 5) === "1"
                    color: root.ink
                }
            }
        }
    }
}
