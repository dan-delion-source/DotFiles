import QtQuick
import QtTest
import "../../bar/BarGeometry.js" as Geometry

TestCase {
    name: "BarGeometry"
    function test_normalize_and_reserve() {
        compare(Geometry.normalize("sideways"), "top")
        compare(Geometry.thickness("top", 36), 36)
        compare(Geometry.thickness("bottom", 36), 36)
        compare(Geometry.thickness("left", 36), 56)
        compare(Geometry.thickness("left", 48, 40), 40)
        compare(Geometry.thickness("right", 24, 100), 100)
        compare(Geometry.thickness("top", 36, 100), 36)
        compare(Geometry.sideWidth(-10), 30)
        compare(Geometry.sideWidth(12), 30)
        compare(Geometry.barHeight(8), 24)
        compare(Geometry.barHeight(0), 24)
        compare(Geometry.barHeight(NaN), 32)
        compare(Geometry.sideWidth(900), 120)
        compare(Geometry.sideWidth(NaN), 56)
        compare(Geometry.thickness("left", 36), Geometry.thickness("right", 36))
    }
    function test_picker_proportions_follow_edge() {
        for (const edge of ["top", "bottom", "left", "right"]) {
            const size = Geometry.pickerSize(edge)
            compare(size.height > size.width, Geometry.vertical(edge))
            const nativeGame = {width: 800, height: 560}
            const frame = Geometry.gameFrameSize(edge, nativeGame)
            if (Geometry.vertical(edge)) verify(frame.height > frame.width)
            else compare(frame, nativeGame)
        }
    }
    function test_side_popup_gap_does_not_grow_with_edge_margin() {
        for (const margin of [0, 16, 32]) {
            for (const barWidth of [30, 56, 120]) {
                const reserve = margin + barWidth
                const left = Geometry.popup("left", 1280, 800, 360, 620, reserve, margin, 4)
                const right = Geometry.popup("right", 1280, 800, 360, 620, reserve, margin, 4)
                compare(left.x - reserve, 4)
                compare(1280 - reserve - (right.x + 360), 4)
            }
        }
    }
    function test_popups_stay_inside_and_open_toward_screen() {
        for (const size of [[1920,1080], [800,600], [600,800]]) {
            for (const edge of ["left", "right", "bottom"]) {
                const reserve = Geometry.thickness(edge, 36) + 12
                const width = Math.min(420, size[0] - reserve - 24)
                const height = Math.min(540, size[1] - (edge === "bottom" ? reserve : 0) - 24)
                const rect = Geometry.popup(edge, size[0], size[1], width, height, reserve, 12)
                verify(rect.x >= 12 && rect.y >= 12)
                verify(rect.x + width <= size[0] - 12)
                verify(rect.y + height <= size[1] - 12)
                if (edge === "left") verify(rect.x >= reserve)
                if (edge === "right") verify(rect.x + width <= size[0] - reserve)
                if (edge === "bottom") verify(rect.y + height <= size[1] - reserve)
            }
        }
    }
}
