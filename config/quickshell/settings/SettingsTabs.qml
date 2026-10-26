import QtQuick
import QtQuick.Controls as QQC
import "../theme"

// Local to Settings: the bar and other shell panels keep their own tabs.
Flickable {
    id: root

    property var tabs: []
    property string current: ""
    signal picked(string id)

    implicitHeight: 36
    visible: root.tabs.length > 1
    clip: true
    contentWidth: links.width
    contentHeight: height
    flickableDirection: Flickable.HorizontalFlick
    boundsBehavior: Flickable.StopAtBounds

    function reveal(button: var): void {
        if (button.x < root.contentX)
            root.contentX = button.x
        else if (button.x + button.width > root.contentX + root.width)
            root.contentX = Math.max(0, button.x + button.width - root.width)
    }

    function revealCurrent(): void {
        for (let i = 0; i < entries.count; ++i) {
            const button = entries.itemAt(i)
            if (button && button.selected) root.reveal(button)
        }
    }

    onCurrentChanged: Qt.callLater(root.revealCurrent)
    onTabsChanged: Qt.callLater(root.revealCurrent)
    onWidthChanged: Qt.callLater(root.revealCurrent)

    Row {
        id: links
        width: childrenRect.width
        height: root.height
        spacing: 6

        Repeater {
            id: entries
            model: root.tabs

            QQC.AbstractButton {
                id: button
                required property var modelData
                readonly property bool selected: root.current === button.modelData.id
                width: label.implicitWidth + 28
                height: root.height
                focusPolicy: Qt.StrongFocus
                Accessible.name: button.modelData.label
                onClicked: root.picked(button.modelData.id)

                background: Rectangle {
                    radius: 8
                    color: button.selected ? Theme.accent
                        : button.hovered ? Theme.islandSurface : "transparent"
                    border.width: button.visualFocus ? 1 : 0
                    border.color: Theme.text
                }

                contentItem: Text {
                    id: label
                    text: button.modelData.label
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSmall
                    font.weight: button.selected ? Font.DemiBold : Font.Normal
                    color: button.selected ? Theme.accentText : Theme.textMuted
                }
            }
        }
    }
}
