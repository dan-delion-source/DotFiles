import QtQuick
import "../../../components"
Card {
    property int rows: 2
    signal panelRequested(string panel)
    WaterTracker { anchors.fill: parent; compact: true }
}
