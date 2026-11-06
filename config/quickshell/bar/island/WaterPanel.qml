import QtQuick
import QtQuick.Layouts
import "../../components"

ColumnLayout {
    signal closed()
    WaterTracker { Layout.fillWidth: true; Layout.fillHeight: true }
}
