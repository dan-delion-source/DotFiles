"""Isolated settings and upright edge-rail checks; no compositor state changes."""
import shutil
import unittest

import test_lock_styles as integration


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class BarPositionTests(unittest.TestCase):
    def fixture(self):
        fixture = integration.LockStyleIntegrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_position_persists_and_profiles_keep_module_order(self):
        f = self.fixture()
        f.shell('''
            require(SettingsService.barPosition === "top", "existing layout defaults to top");
            SettingsService.setBarZone("left", ["runningCat", "networkSpeed"]);
            for (const edge of ["top", "left", "right", "bottom"]) {
                SettingsService.set("barPosition", edge);
                require(SettingsService.barPosition === edge, "position changes");
                require(SettingsService.barZone("left")[0] === "runningCat", "order retained");
                require(SettingsService.snapshot().barPosition === edge, "included in profile");
            }
            SettingsService.set("barPosition", "invalid");
            require(SettingsService.barPosition === "top", "safe fallback");
            SettingsService.set("barPosition", "right");
            SettingsService.set("barHeight", 12);
            SettingsService.set("sideBarWidth", 16);
            SettingsService.set("spreadBand", true);
            require(SettingsService.barHeight === 24 && SettingsService.sideBarWidth === 30, "minimum sizes enforced");
            require(SettingsService.snapshot().spreadBand, "spread background in profile");
            const height = SettingsService.barHeight;
            SettingsService.set("sideBarWidth", 44);
            require(SettingsService.sideBarWidth === 44, "width adjusts independently");
            require(SettingsService.barHeight === height, "module height retained");
            require(SettingsService.snapshot().sideBarWidth === 44, "width in profile");
            finish.start();
        ''')
        f.shell('''
            require(SettingsService.barPosition === "right", "saved edge after restart");
            require(SettingsService.sideBarWidth === 44, "saved width after restart");
            require(SettingsService.barHeight === 24 && SettingsService.spreadBand, "small height and background saved");
            const saved = SettingsService.snapshot();
            SettingsService.adopt({barPosition: "bottom", sideBarWidth: 112});
            require(SettingsService.sideBarWidth === 112, "profile changes width");
            require(SettingsService.barPosition === "bottom", "profile changes edge");
            SettingsService.adopt(saved);
            require(SettingsService.barPosition === "right", "profile restores edge");
            require(SettingsService.sideBarWidth === 44, "profile restores width");
            require(SettingsService.barZone("left")[0] === "runningCat", "profile restores order");
            finish.start();
        ''')

    def rail_fixture(self):
        f = self.fixture()
        for folder in ("bar", "components", "theme", "assets"):
            shutil.copytree(integration.ROOT / folder, f.root / folder, dirs_exist_ok=True)
        stubs = {
            "SystemService": '''property string powerProfile: "balanced"
                function subscribe() {} function release() {}''',
            "ModuleService": '''property var buttons: ({})
                property var ringed: []
                property string openId: ""
                property string shownPanel: ""
                property int restWidth: 130
                property bool muted: false
                function entry(id) { return {detail: false} }
                function shows(id, when) { return true }
                function isButton(id) { return false }
                function shapeOf(id, own) { return "symbol" }
                function figureOf(own) { return "on" }
                function valueOf(id) { if (id === "battery") return "100%"; if (id === "volume") return muted ? "Muted" : "100%"; return id === "networkSpeed" ? "↓ 12 MB/s  ↑ 3 MB/s" : id === "stats" ? "42%" : "" }
                function figureLimit(id) { return 160 }
                function tintOf(id) { return "#cdd6f4" }
                function glyphOf(id) { return "●" }
                function watch(id, on) {}
                function activate(id) {} function has(id) { return true }''',
            "HyprlandService": '''property int maximum: 5
                property int activeId: 2
                function activeOn(name) { return 2 }
                function isOccupied(id) { return id === 1 || id === 3 }
                function isVisible(id) { return id <= 5 }
                function focus(id) {}''',
            "TrayService": '''property var items: []
                property var item: null
                function activate(item) {} function open(item) {}''',
        }
        for name, body in stubs.items():
            (f.root / "services" / f"{name}.qml").write_text(
                "pragma Singleton\nimport QtQuick\nimport Quickshell\nSingleton { " + body + " }")
        return f

    def test_rails_flow_without_rotation_and_long_groups_scroll(self):
        f = self.rail_fixture()
        f.shell('''
            SettingsService.set("sideBarWidth", 40);
            SettingsService.setBarZone("left", ["workspaces", "runningCat", "networkSpeed"]);
            SettingsService.setBarZone("right", ["stats", "runningCat", "networkSpeed", "stats", "runningCat"]);
            next.start();
        ''', '''
        Window { visible: true; width: 800; height: 650
        Loader { id: left; width: SettingsService.sideBarWidth; height: 450; sourceComponent: EdgeRail { edge: "left" } }
        Loader { id: right; width: SettingsService.sideBarWidth; height: 450; sourceComponent: EdgeRail { edge: "right" } }
        Loader { id: bottom; width: 640; height: 36; sourceComponent: EdgeRail { edge: "bottom" } }
        }
        Timer { id: next; interval: 100; onTriggered: {
            try {
                for (const loader of [left, right, bottom]) {
                    require(loader.status === Loader.Ready, "rail loads");
                    const rail = loader.item;
                    require(rail.rotation === 0, "rail is upright");
                    require(rail.beforeExtent <= rail.zoneRoom && rail.afterExtent <= rail.zoneRoom, "zones fit screen");
                    require(rail.beforeExtent > 0 && rail.afterExtent > 0, "modules are laid out");
                }
                const scroll = findNamed(left.item, "leadingZone");
                require(scroll.contentHeight > scroll.height, "long side group can scroll");
                scroll.contentY = scroll.contentHeight - scroll.height;
                require(scroll.contentY > 0, "last items are reachable");
                left.item.unified = true;
                require(left.item.usedExtent >= left.item.centreExtent + 2 * Math.max(left.item.beforeExtent, left.item.afterExtent), "unified ground covers both zones");
                require(left.item.vertical && right.item.vertical && !bottom.item.vertical, "edge orientation");
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar"\n')

    def test_spread_side_clock_is_a_taller_column_with_date(self):
        f = self.rail_fixture()
        f.shell('''
            SettingsService.set("sideBarWidth", 40);
            SettingsService.set("clockShowsDate", true);
            SettingsService.set("clockShowsSeconds", true);
            SettingsService.set("clockFormat", "h:mm AP");
            next.start();
        ''', '''
        Window { visible: true; width: 300; height: 700
            EdgeRail { id: rail; edge: "left"; width: SettingsService.sideBarWidth;
                height: 650; spread: true; unified: false }
        }
        Timer { id: next; interval: 100; onTriggered: {
            try {
                const clock = findNamed(rail, "spreadColumnClock");
                const button = findNamed(rail, "sideIslandButton");
                require(clock.visible && clock.timeText.split("\\n").length === 4, "hours minutes seconds and period stack");
                require(clock.showDate && clock.dateText.indexOf("\\n") > 0, "date beneath time");
                const tall = rail.centreExtent;
                require(tall >= 112 && button.height === tall, "taller centre capsule");
                require(button.width === 40, "independent width retained");
                rail.spread = false;
                require(!clock.visible && rail.centreExtent < tall, "other styles stay compact");
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar"\n')

    def test_small_sizes_and_spread_black_background(self):
        f = self.rail_fixture()
        f.shell('''
            SettingsService.set("barHeight", 8);
            SettingsService.set("sideBarWidth", 12);
            SettingsService.set("spreadBand", true);
            SettingsService.setBarZone("left", ["runningCat", "workspaces"]);
            SettingsService.setBarZone("right", ["stats", "networkSpeed"]);
            next.start();
        ''', '''
        Window { visible: true; width: 400; height: 700
            EdgeRail { id: rail; edge: "left"; width: SettingsService.sideBarWidth;
                height: 650; spread: true; unified: false }
            EdgeRail { id: bottom; edge: "bottom"; width: 300;
                height: SettingsService.barHeight; spread: true; unified: false }
        }
        Timer { id: next; interval: 100; onTriggered: {
            try {
                require(rail.width === 30 && bottom.height === 24, "minimum dimensions applied");
                for (const item of [rail, bottom]) {
                    const ground = findNamed(item, "railBackground");
                    require(item.banded && ground.visible, "spread background enabled");
                    require(ground.color.r === 0 && ground.color.g === 0 && ground.color.b === 0 && ground.color.a === 1, "opaque black");
                    require(item.vertical ? ground.height === item.height : ground.width === item.width, "full length background");
                }
                for (const item of [rail, bottom]) {
                    const first = findNamed(item, "leadingZone");
                    const last = findNamed(item, "trailingZone");
                    require(item.vertical ? first.y >= 12 : first.x >= 12, "leading padding");
                    require(item.vertical ? last.y + last.height <= item.height - 12
                        : last.x + last.width <= item.width - 12, "trailing padding");
                    if (item.vertical) require(first.x >= 4 && first.width <= item.width - 8, "cross-axis padding");
                }
                SettingsService.set("spreadBand", false);
                require(!rail.banded && !findNamed(rail, "railBackground").visible, "floating mode restored");
                require(SettingsService.barZone("left")[0] === "runningCat", "placement retained");
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar"\n')

    def test_notch_suppresses_band_without_erasing_saved_choice(self):
        f = self.rail_fixture()
        f.shell('''
            SettingsService.set("barStyle", "spread");
            SettingsService.set("barPosition", "top");
            SettingsService.set("spreadBand", true);
            require(rail.banded && !SettingsService.barNotched, "floating band enabled");
            SettingsService.set("islandAttached", true);
            require(SettingsService.barNotched && !rail.banded, "notch suppresses band");
            require(SettingsService.snapshot().spreadBand, "saved preference retained");
            SettingsService.set("islandAttached", false);
            require(!SettingsService.barNotched && rail.banded, "floating restores band");
            SettingsService.set("islandAttached", true);
            SettingsService.set("barPosition", "left");
            require(!SettingsService.barNotched && rail.banded, "remembered top notch does not affect side bar");
            finish.start();
        ''', '''EdgeRail { id: rail; edge: SettingsService.barPosition; width: 60; height: 500 }''',
                imports='import "./bar"\n')

    def test_side_percentages_fit_and_clock_uses_module_scale(self):
        f = self.rail_fixture()
        f.shell('''
            SettingsService.set("sideBarWidth", 30);
            next.start();
        ''', '''
        Window { visible: true; width: 300; height: 500
            ChipFace { id: battery; vertical: true; moduleId: "battery"; reveal: 1 }
            ChipFace { id: volume; y: 100; vertical: true; moduleId: "volume"; reveal: 1 }
            StackedClock { id: clock; y: 200; width: SettingsService.sideBarWidth; height: implicitHeight }
        }
        Timer { id: next; interval: 100; onTriggered: {
            try {
                for (const chip of [battery, volume]) {
                    const value = findNamed(chip, "chipValue");
                    require(value.text === "100%" && !value.truncated, "full percentage visible at minimum width");
                    require(value.contentWidth <= value.width + 1, "value fits available width");
                    require(value.font.pixelSize <= 11, "compact side typography");
                }
                const time = findNamed(clock, "stackedClockTime");
                require(time.font.pixelSize <= 12, "clock matches modules");
                ModuleService.muted = true;
                mutedCheck.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        Timer { id: mutedCheck; interval: 50; onTriggered: {
            try {
                const value = findNamed(volume, "chipValue");
                require(value.text === "Muted" && !value.truncated, "muted label fits too");
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar/modules"\nimport "./components"\n')
