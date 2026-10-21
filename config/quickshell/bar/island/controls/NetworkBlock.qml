import QtQuick
import QtQuick.Layouts
import Quickshell

import "../../../theme"
import "../../../services"
import "../../../components"

// Connection shortcut in the control centre. The whole block opens the
// separate Network Manager page, even when Wi-Fi is off or Ethernet is used.
Card {
    id: root

    property int rows: 1
    signal requested()

    padding: root.rows >= 2 ? 14 : 8

    border.color: press.containsMouse ? Theme.accent : Theme.borderIn(QsWindow.window)
    Behavior on border.color { ColorAnimation { duration: Theme.durationFast } }

    ColumnLayout {
        anchors.fill: parent
        spacing: 5

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: NetworkService.icon
                font.family: Theme.fontMono
                font.pixelSize: 17
                color: NetworkService.wifiConnected || NetworkService.wiredConnected
                    ? Theme.indicator : Theme.textMuted
            }

            Text {
                Layout.fillWidth: true
                text: NetworkService.connectionName
                elide: Text.ElideRight
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeSmall
                font.weight: Font.DemiBold
                color: Theme.text
            }

            Text {
                text: "󰅂"
                font.family: Theme.fontMono
                font.pixelSize: 13
                color: press.containsMouse ? Theme.accent : Theme.textMuted
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.fillHeight: true
            text: NetworkService.stateLine
            elide: Text.ElideRight
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fontSizeLabel
            color: Theme.textMuted
        }
    }

    MouseArea {
        id: press
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.requested()
    }
}
