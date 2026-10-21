import QtQuick
import QtQuick.Layouts
import "../theme"
import "../services"

// Shared rate labels and histories for the control-center block and detail.
ColumnLayout {
    id: root
    property bool graphs: false
    spacing: 8

    RowLayout {
        Layout.fillWidth: true
        spacing: 12
        Repeater {
            model: [
                { label: "↓ Download", rate: StatsService.networkDown },
                { label: "↑ Upload", rate: StatsService.networkUp }
            ]
            ColumnLayout {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                spacing: 3
                Text {
                    Layout.fillWidth: true
                    text: modelData.label
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeLabel
                    color: Theme.textMuted
                    elide: Text.ElideRight
                }
                Text {
                    Layout.fillWidth: true
                    text: StatsService.networkAvailable ? StatsService.rate(modelData.rate) : StatsService.networkStatus
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSizeSmall
                    font.features: { "tnum": 1 }
                    color: Theme.text
                    elide: Text.ElideRight
                }
            }
        }
    }
    RowLayout {
        visible: root.graphs
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: root.graphs ? 28 : 0
        spacing: 12
        Sparkline {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            values: StatsService.downHistory
            maximum: 0
            stroke: Theme.accent
            opacity: StatsService.networkAvailable ? 1 : 0.35
        }
        Sparkline {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredWidth: 1
            values: StatsService.upHistory
            maximum: 0
            stroke: Theme.blue
            opacity: StatsService.networkAvailable ? 1 : 0.35
        }
    }
}
