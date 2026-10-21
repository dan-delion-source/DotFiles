import QtQuick
import QtQuick.Layouts
import "../../../theme"
import "../../../services"
import "../../../components"

Card {
    id: root
    property int rows: 1
    ColumnLayout {
        anchors.fill: parent
        spacing: 6
        RowLayout {
            visible: root.rows >= 2
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Network Speed"
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeSmall
                font.weight: Font.DemiBold
                color: Theme.text
                elide: Text.ElideRight
            }
            Text {
                visible: !StatsService.networkAvailable
                text: StatsService.networkStatus
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fontSizeLabel
                color: Theme.textMuted
            }
        }
        NetworkRates {
            Layout.fillWidth: true
            Layout.fillHeight: true
            graphs: root.rows >= 2
        }
    }
}
