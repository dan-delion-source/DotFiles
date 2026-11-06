"""Daily water persistence, rollover, goal, and old-layout migration."""
import json
from pathlib import Path
import shutil
import unittest
import os
from unittest.mock import patch
import test_lock_styles as integration


@unittest.skipUnless(shutil.which('qs'), 'QuickShell is required')
class WaterTests(unittest.TestCase):
    def fixture(self):
        f = integration.LockStyleIntegrationTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        for name in ['WaterService.qml', 'WaterLogic.js']:
            shutil.copy2(integration.ROOT / 'services' / name, f.root / 'services' / name)
        return f

    def test_toggle_goal_undo_and_restart_persistence(self):
        f = self.fixture()
        f.shell('''
            if (!WaterService.ready) { wait.start(); return }
            exercise();
        ''', '''
        property int goals: 0
        Connections { target: WaterService; function onGoalReached() { goals++ } }
        function exercise() {
            require(WaterService.count === 0, "starts empty");
            WaterService.toggle(6);
            require(WaterService.count === 1 && WaterService.filled(6) && !WaterService.filled(0), "only selected glass fills");
            WaterService.toggle(6);
            require(WaterService.count === 0, "undo works");
            WaterService.toggle(-1); WaterService.toggle(8);
            require(WaterService.count === 0, "invalid indexes ignored");
            for (let i = 0; i < 8; i++) WaterService.toggle(i);
            require(WaterService.count === 8 && WaterService.complete && goals === 1, "eighth glass celebrates once");
            finish.start();
        }
        Timer { id: wait; interval: 10; repeat: true; onTriggered: { if (WaterService.ready) { stop(); exercise() } } }
        ''')
        saved = json.loads((f.root / 'state/danshell/water.json').read_text())
        self.assertEqual(saved['mask'], 255)
        f.shell('''
            if (!WaterService.ready) { wait.start(); return }
            verifySaved();
        ''', '''
        function verifySaved() {
            require(WaterService.count === 8 && WaterService.complete, "same-day progress restored");
            WaterService.toggle(7);
            require(WaterService.count === 7 && !WaterService.complete, "completed day can be corrected");
            finish.start();
        }
        Timer { id: wait; interval: 10; repeat: true; onTriggered: { if (WaterService.ready) { stop(); verifySaved() } } }
        ''')

    def test_old_day_resets_and_reminder_window_is_bounded(self):
        f = self.fixture()
        (f.root / 'state/danshell/water.json').write_text(json.dumps({'day': '2000-01-01', 'mask': 255}))
        f.shell('''
            if (!WaterService.ready) { wait.start(); return }
            verifyDay();
        ''', '''
        function verifyDay() {
            require(WaterService.count === 0 && !WaterService.complete, "previous day resets");
            const morning = new Date(2026, 4, 8, 9, 0).getTime();
            require(WaterLogic.reminderDue(morning, morning - 5400000, 0), "reminder at 9 AM");
            require(!WaterLogic.reminderDue(morning, morning - 5399999, 0), "never early");
            require(!WaterLogic.reminderDue(morning, morning - 5400000, 255), "stops at goal");
            const night = new Date(2026, 4, 8, 21, 0).getTime();
            require(!WaterLogic.reminderDue(night, morning, 0), "quiet after 9 PM");
            require(WaterLogic.dayKey(new Date(2026, 4, 8, 23, 59).getTime()) === "2026-05-08", "uses local day");
            require(WaterLogic.dayKey(new Date(2026, 4, 9, 0, 0).getTime()) === "2026-05-09", "midnight changes day");
            finish.start();
        }
        Timer { id: wait; interval: 10; repeat: true; onTriggered: { if (WaterService.ready) { stop(); verifyDay() } } }
        ''', imports='import "./services/WaterLogic.js" as WaterLogic\n')

    def test_layout_and_imported_profile_replace_pet_without_losing_placement(self):
        f = self.fixture()
        (f.root / 'state/danshell/settings.json').write_text(json.dumps({
            'barLeft': ['workspaces', {'id': 'pet', 'figure': 'always'}, 'runningCat'],
            'barRight': ['volume', 'battery'],
            'centreBlocks': [{'id': 'pet', 'col': 2, 'row': 3, 'size': '2x3'}],
            'centreTop': {'left': ['pet'], 'right': ['games']}
        }))
        f.shell('''
            require(SettingsService.barZone("left")[1] === "water", "bar placement migrated");
            require(SettingsService.barItems("left")[1].figure === "always", "chip options kept");
            require(SettingsService.centreBlocks[0].id === "water" && SettingsService.centreBlocks[0].row === 3, "block placement kept");
            require(SettingsService.centreTop.left[0] === "water", "door migrated");
            SettingsService.adopt({barLeft: ["pet", "clock"]});
            require(SettingsService.barZone("left")[0] === "water", "old profiles migrate too");
            require(!("petStyle" in SettingsService.snapshot()), "old style setting gone");
            finish.start();
        ''')

    def test_reminder_delivery_is_throttled_and_respects_do_not_disturb(self):
        f = self.fixture()
        (f.root / "bin").mkdir()
        command = f.root / "bin/notify-send"
        command.write_text('#!/usr/bin/env python3\nimport os,sys,json\nfrom pathlib import Path\np=Path(os.environ["XDG_STATE_HOME"])/"notifications.jsonl"\nwith p.open("a") as out: out.write(json.dumps(sys.argv[1:])+"\\n")\n')
        command.chmod(0o755)
        with patch.dict(os.environ, {"PATH": str(f.root / "bin") + os.pathsep + os.environ["PATH"]}):
            f.shell('''
                if (!WaterService.ready) { wait.start(); return }
                exercise();
            ''', '''
            function exercise() {
                const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1); tomorrow.setHours(9, 0, 0, 0);
                const morning = tomorrow.getTime();
                WaterService.tick(morning);
                WaterService.tick(morning + 5400000);
                WaterService.tick(morning + 5400001);
                SettingsService.set("doNotDisturb", true);
                WaterService.tick(morning + 10800000);
                finish.start();
            }
            Timer { id: wait; interval: 10; repeat: true; onTriggered: { if (WaterService.ready) { stop(); exercise() } } }
            ''')
        notifications = (f.root / "state/notifications.jsonl").read_text().splitlines()
        self.assertEqual(len(notifications), 1)
        self.assertIn("Time for a glass of water", json.loads(notifications[0]))

    def test_glass_click_animation_and_congratulations_view(self):
        f = self.fixture()
        (f.root / 'components').mkdir()
        for name in ['WaterGlass.qml', 'WaterTracker.qml', 'PillButton.qml']:
            shutil.copy2(integration.ROOT / 'components' / name, f.root / 'components' / name)
        (f.root / 'theme/Theme.qml').write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
 property real motion: 1
 property string fontFamily: "Sans Serif"
 property string fontMono: "Monospace"
 property int fontSizeSmall: 11
 property int fontSizeMedium: 14
 property int fontSizeLarge: 16
 property int fontSizeLabel: 10
 property int cardFigure: 24
 property int radiusPill: 14
 property int durationFast: 140
 property int durationMedium: 200
 property int durationMorph: 380
 property color text: "#eeeeee"
 property color textMuted: "#929292"
 property color surface: "#181818"
 property color surfaceHover: "#242424"
 property color accent: "#45bfff"
 property color accentHover: "#70cfff"
 property color accentText: "#101010"
 property color red: "#ff7777"
 function surfaceIn(window) { return surface }
 function surfaceHoverIn(window) { return surfaceHover }
 function borderIn(window) { return "#333333" }
}''')
        f.shell('''
            if (!WaterService.ready) { wait.start(); return }
            exercise();
        ''', '''
        FloatingWindow { visible: true; implicitWidth: 520; implicitHeight: 380; color: "#101010"
            WaterTracker { id: tracker; anchors.fill: parent; anchors.margins: 22 }
        }
        TestCase { id: mouse; name: "WaterView"; when: false }
        function exercise() {
            tracker.grabToImage(result => result.saveToFile("/tmp/water-empty.png"));
            mouse.mouseClick(findNamed(tracker, "waterGlass3"));
            require(WaterService.count === 1 && WaterService.filled(3), "click logs chosen glass");
            for (let i = 0; i < 8; i++) if (i !== 3) require(!WaterService.filled(i), "other glasses stay empty");
            animation.start();
        }
        Timer { id: wait; interval: 10; repeat: true; onTriggered: { if (WaterService.ready) { stop(); exercise() } } }
        Timer { id: animation; interval: 600; onTriggered: {
            try {
                require(findNamed(tracker, "waterGlass3").level > 0.99, "fill animation finishes");
                require(findNamed(tracker, "waterGlass0").level === 0, "empty glass remains monochrome");
                tracker.grabToImage(result => result.saveToFile("/tmp/water-one-glass.png"));
                remaining.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit() }
        } }
        Timer { id: remaining; interval: 100; onTriggered: {
            try {
                for (let i = 0; i < 8; i++) if (i !== 3) mouse.mouseClick(findNamed(tracker, "waterGlass" + i));
                require(WaterService.complete && tracker.celebrating, "completion screen shown");
                capture.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit() }
        } }
        Timer { id: capture; interval: 500; onTriggered: {
            tracker.grabToImage(result => result.saveToFile("/tmp/water-complete.png")); finish.start();
        } }
        ''', imports='import QtTest\nimport "./components"\n')


if __name__ == '__main__':
    unittest.main()
