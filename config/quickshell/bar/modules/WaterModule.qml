import QtQuick
import "../../theme"
import "../../services"
import "../../components"

Item {
    id: root
    property bool compact: false
    WaterGlass {
        anchors.centerIn: parent
        visible: root.compact
        width: Theme.capsuleHeight * 0.65
        height: Theme.capsuleHeight * 0.8
        drank: WaterService.count > 0
        interactive: false
    }
    WaterTracker { anchors.fill: parent; anchors.margins: 14; compact: true; visible: !root.compact }
}
