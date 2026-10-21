// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   P O P   M E N U                                                        │
// │   context menu · opened at the click position                            │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import QtQuick.Layouts
import Quickshell

import "../theme"

Item {
    id: root

    property var rows: []

    signal chosen(string id)

    implicitWidth: Theme.menuWidth
    implicitHeight: column.implicitHeight + 2 * Theme.menuPadding
    width: implicitWidth
    height: implicitHeight

    Rectangle {
        anchors.fill: parent
        radius: Theme.radiusMedium
        color: Theme.island
        border.color: Theme.borderIn(QsWindow.window)
        border.width: 1
    }

    ColumnLayout {
        id: column

        anchors.fill: parent
        anchors.margins: Theme.menuPadding
        spacing: 0

        Repeater {
            model: ScriptModel {
                values: root.rows
            }

            Rectangle {
                id: row

                required property var modelData

                Layout.fillWidth: true
                Layout.preferredHeight: Theme.menuRow
                radius: Theme.radiusSmall
                color: rowMouse.containsMouse ? Theme.surfaceHoverIn(QsWindow.window) : "transparent"

                Behavior on color { ColorAnimation { duration: Theme.durationFast } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 10

                    Text {
                        Layout.preferredWidth: 16
                        horizontalAlignment: Text.AlignHCenter
                        text: row.modelData.icon ?? ""
                        font.family: Theme.fontMono
                        font.pixelSize: 12
                        color: row.modelData.warn && rowMouse.containsMouse
                            ? Theme.red : Theme.textMuted
                    }

                    Text {
                        Layout.fillWidth: true
                        text: row.modelData.label
                        elide: Text.ElideRight
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fontSizeSmall
                        color: row.modelData.warn && rowMouse.containsMouse
                            ? Theme.red : Theme.text
                    }
                }

                MouseArea {
                    id: rowMouse

                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.chosen(row.modelData.id)
                }
            }
        }
    }
}
