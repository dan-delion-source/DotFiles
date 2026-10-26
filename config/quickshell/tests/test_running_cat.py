"""Original sprite integrity and isolated bar-module persistence/lifecycle."""
import hashlib
import json
import shutil
import unittest

import test_lock_styles as integration

ROOT = integration.ROOT


class RunningCatTests(unittest.TestCase):
    def test_original_zenith_frames_are_unchanged(self):
        hashes = [
            "1cc30f411060e57b98ce63f19df78d92e427344163b897131feeb4567f342626",
            "d1edc482c28d162f373e9531aa4faec4f00b389094e0298d0280f927e0d1697e",
            "05aa7f16fd84569b2624f9d8fb3b0c46e9bd54c3e364992ccc279b5dedce6802",
            "2eb25aea4bcfb4a9208b5608acb1603f61d20135a28b2c55809d0d2c2ff3a599",
        ]
        for index, expected in enumerate(hashes):
            sprite = ROOT / f"assets/running-cat/cat_f{index}.png"
            self.assertEqual(hashlib.sha256(sprite.read_bytes()).hexdigest(), expected)

    @unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
    def test_saved_placement_and_balanced_watcher_lifecycle(self):
        fixture = integration.LockStyleIntegrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for folder in ("components", "bar/modules", "assets/running-cat"):
            (fixture.root / folder).mkdir(parents=True)
        for name in ("components/RunningCat.qml", "bar/modules/RunningCatModule.qml"):
            shutil.copy2(ROOT / name, fixture.root / name)
        for sprite in (ROOT / "assets/running-cat").glob("*.png"):
            shutil.copy2(sprite, fixture.root / "assets/running-cat" / sprite.name)
        (fixture.root / "theme/Theme.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton { property int capsuleHeight: 30 }''')
        (fixture.root / "services/SystemService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property string powerProfile: "balanced"
    property int watchers: 0
    function subscribe() { watchers++ }
    function release() { watchers-- }
}''')
        # The production module uses a fake sampler; no hardware or daemon runs.
        fixture.shell('''
            const cat = holder.item;
            require(cat.interval === 150 && cat.size === 35, "upstream timing and scale");
            require(SystemService.watchers === 1, "single sampler subscription");
            cat.visible = false;
            require(SystemService.watchers === 0, "hidden module releases sampler");
            cat.visible = true;
            SettingsService.set("motionScale", 0);
            require(!cat.animating && SystemService.watchers === 0, "motion off releases sampler");
            SettingsService.set("motionScale", 100);
            require(SystemService.watchers === 1, "motion resumes subscription");
            holder.active = false;
            require(SystemService.watchers === 0, "removal releases sampler");
            SettingsService.setBarZone("left", ["clock", "runningCat", "split", "timer"]);
            SettingsService.setBarZone("right", ["tray"]);
            require(SettingsService.barZone("left")[1] === "runningCat", "ordered placement");
            finish.start();
        ''', '''Loader {
            id: holder
            source: "bar/modules/RunningCatModule.qml"
        }''')
        saved = json.loads((fixture.root / "state/danshell/settings.json").read_text())
        self.assertEqual(saved["barLeft"], ["clock", "runningCat", "split", "timer"])
        fixture.shell('''
            require(SettingsService.barZone("left")[1] === "runningCat", "placement survives restart");
            SettingsService.setBarZone("left", ["clock", "timer"]);
            SettingsService.setBarZone("right", ["tray", "runningCat"]);
            require(SettingsService.barZone("right")[1] === "runningCat", "move to other side");
            finish.start();
        ''')
