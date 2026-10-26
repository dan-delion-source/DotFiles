import QtQuick
import "../theme"

// A taller resting face for the side bar in Spread mode.
Item {
    id: root
    property date date: new Date()
    property string format: "HH:mm"
    property bool showSeconds: false
    property bool showDate: false
    property real minimumHeight: Theme.capsuleHeight * 3.5
    readonly property string timeText: Qt.formatDateTime(root.date,
        (root.showSeconds ? root.format.replace("mm", "mm:ss") : root.format)
            .replace(/:/g, "\n").replace(/\s+AP/, "\nAP"))
    readonly property string dateText: Qt.formatDateTime(root.date, "ddd\nd MMM")
    implicitHeight: Math.max(root.minimumHeight, content.implicitHeight + 32)

    Column {
        id: content
        anchors.centerIn: parent
        width: Math.max(1, parent.width - 12)
        spacing: 8
        Text {
            width: parent.width
            objectName: "stackedClockTime"
            text: root.timeText
            horizontalAlignment: Text.AlignHCenter
            font.family: Theme.fontFamily
            font.pixelSize: Theme.sideClockFontSize
            font.weight: Font.DemiBold
            font.features: { "tnum": 1 }
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: 1
            lineHeight: 1.15
            color: Theme.text
        }
        Rectangle {
            visible: root.showDate
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(18, parent.width)
            height: 1
            color: Qt.alpha(Theme.accent, 0.6)
        }
        Text {
            visible: root.showDate
            width: parent.width
            text: root.dateText
            horizontalAlignment: Text.AlignHCenter
            font.family: Theme.fontFamily
            font.pixelSize: Math.max(7, Theme.sideFigureFontSize - 1)
            fontSizeMode: Text.HorizontalFit
            minimumPixelSize: 1
            lineHeight: 1.25
            color: Theme.textMuted
        }
    }
}
