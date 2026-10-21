import QtQuick
import QtQuick.Layouts
import "../../theme"
import "../../services"
import "../../components"

Item {
    ModuleCard {
        title: "Network Speed"
        subtitle: StatsService.networkAvailable ? "All interfaces · " + StatsService.window : StatsService.networkStatus
        mark: Text {
            anchors.centerIn: parent
            text: "󰓅"
            font.family: Theme.fontMono
            font.pixelSize: 24
            color: Theme.text
        }
        NetworkRates {
            Layout.fillWidth: true
            Layout.fillHeight: true
            graphs: true
        }
    }
}
