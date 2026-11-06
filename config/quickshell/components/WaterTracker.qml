import QtQuick
import QtQuick.Layouts
import "../theme"
import "../services"

Item {
    id: root
    property bool compact: false
    property bool celebrating: false
    implicitHeight: compact ? 198 : 320
    Connections {
        target: WaterService
        function onGoalReached(): void { if (root.visible) root.celebrating = true }
        function onCompleteChanged(): void { if (!WaterService.complete) root.celebrating = false }
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: root.compact ? 6 : 12
        visible: !root.celebrating
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Water"; font.family: Theme.fontFamily; font.pixelSize: root.compact ? Theme.fontSizeMedium : Theme.fontSizeLarge; font.weight: Font.DemiBold; color: Theme.text }
            Item { Layout.fillWidth: true }
            Text { objectName: "waterCount"; text: `${WaterService.count} / 8`; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeMedium; font.weight: Font.DemiBold; color: WaterService.count > 0 ? WaterService.blue : Theme.textMuted }
        }
        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 4
            columnSpacing: root.compact ? 4 : 12
            rowSpacing: root.compact ? 2 : 8
            Repeater {
                model: 8
                WaterGlass {
                    required property int index
                    objectName: "waterGlass" + index
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.maximumHeight: root.compact ? 62 : 108
                    number: index + 1
                    drank: WaterService.filled(index)
                    interactive: WaterService.ready
                    onActivated: WaterService.toggle(index)
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: WaterService.error || (root.compact ? "Today · tap a glass to log" : "Tap a glass to log it. Tap again to undo.\nReminders every 90 minutes · 9 AM–9 PM")
            wrapMode: Text.Wrap
            font.family: Theme.fontFamily
            font.pixelSize: root.compact ? Theme.fontSizeLabel : Theme.fontSizeSmall
            color: WaterService.error ? Theme.red : Theme.textMuted
        }
    }
    Rectangle {
        objectName: "waterCongratulations"
        anchors.fill: parent
        visible: root.celebrating
        color: Theme.surface
        radius: 14
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.compact ? 10 : 24
            spacing: 10
            Item { Layout.fillHeight: true }
            Text { Layout.fillWidth: true; text: "Congratulations!"; horizontalAlignment: Text.AlignHCenter; font.family: Theme.fontFamily; font.pixelSize: root.compact ? Theme.fontSizeLarge : Theme.cardFigure; font.weight: Font.DemiBold; color: WaterService.blue }
            Text { Layout.fillWidth: true; text: "All 8 glasses logged today."; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap; font.family: Theme.fontFamily; font.pixelSize: Theme.fontSizeSmall; color: Theme.text }
            PillButton { Layout.alignment: Qt.AlignHCenter; text: "Back to glasses"; onClicked: root.celebrating = false }
            Item { Layout.fillHeight: true }
        }
        opacity: visible ? 1 : 0
        scale: visible ? 1 : 0.96
        Behavior on opacity { NumberAnimation { duration: Theme.durationMedium } }
        Behavior on scale { NumberAnimation { duration: Theme.durationMorph; easing.type: Easing.OutCubic } }
    }
}
