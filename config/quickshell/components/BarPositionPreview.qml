import QtQuick
import "../theme"

Rectangle {
    id: root
    property string edge: "top"
    readonly property bool vertical: root.edge === "left" || root.edge === "right"
    implicitWidth: 124
    implicitHeight: 68
    color: Theme.background
    radius: 8
    border.width: 1
    border.color: Theme.islandRim
    Rectangle {
        x: root.vertical ? (root.edge === "left" ? 7 : root.width - width - 7) : 12
        y: root.vertical ? 8 : root.edge === "bottom" ? root.height - height - 7 : 7
        width: root.vertical ? 12 : root.width - 24
        height: root.vertical ? root.height - 16 : 9
        radius: 5
        color: Theme.accent
        Rectangle {
            anchors.centerIn: parent
            width: root.vertical ? 5 : 22
            height: root.vertical ? 16 : 5
            radius: 3
            color: Theme.accentText
        }
    }
    Rectangle {
        x: root.edge === "left" ? 25 : 12
        y: root.edge === "top" ? 24 : 10
        width: root.vertical ? root.width - 37 : root.width - 24
        height: root.vertical ? root.height - 20 : root.height - 34
        radius: 4
        color: Theme.surface
    }
}
