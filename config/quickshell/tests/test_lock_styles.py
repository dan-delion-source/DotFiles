"""Offscreen integration checks; no real lock surface or PAM conversation starts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class LockStyleIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="danshell-lock-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("services", "theme", "state/danshell", "data", "cache"):
            (self.root / folder).mkdir(parents=True)
        (self.root / "runtime").mkdir(mode=0o700)
        shutil.copytree(ROOT / "lock", self.root / "lock")
        (self.root / "bar").mkdir()
        shutil.copy2(ROOT / "bar/BarGeometry.js", self.root / "bar/BarGeometry.js")
        for name in ("SettingsService.qml", "LockService.qml"):
            shutil.copy2(ROOT / "services" / name, self.root / "services" / name)
        # No camera discovery or authentication helper can run in these tests.
        (self.root / "services/FaceService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property bool listed: true
    property var faces: []
    function refresh(): void {}
}''')
        (self.root / "services/AccountService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton { property string name: "Test account" }''')
        (self.root / "theme/Theme.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property real motion: 0
    property color text: "#cdd6f4"
    property color accent: "#89b4fa"
    property color red: "#f38ba8"
}''')
        # Only the fallback's contract is exercised here. Classic's rendering
        # remains covered by the full configuration compile/layout checks.
        (self.root / "lock/LockSurface.qml").write_text('''import QtQuick
Item {
    property string output: ""
    property bool claimed: false
    signal submitted(string password)
    function claim(): void { claimed = true }
}''')

    def shell(self, body, objects="", imports=""):
        (self.root / "shell.qml").write_text('''import QtQuick
import Quickshell
import "./services"
import "./lock"
''' + imports + '''
ShellRoot {
    id: harness
    function findNamed(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children ?? []) {
            const found = findNamed(child, name);
            if (found) return found;
        }
        return null;
    }
    function require(value, message) {
        if (!value) throw new Error(message);
    }
    ''' + objects + '''
    Timer {
        interval: 40; running: true; repeat: true
        onTriggered: {
            if (!SettingsService.arrived) return;
            stop();
            try { ''' + body + '''
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        }
    }
    Timer { id: finish; interval: 100; onTriggered: { console.log("LOCK_TEST_OK"); Qt.quit(); } }
}''')
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
                   XDG_RUNTIME_DIR=str(self.root / "runtime"),
                   XDG_STATE_HOME=str(self.root / "state"),
                   XDG_DATA_HOME=str(self.root / "data"),
                   XDG_CACHE_HOME=str(self.root / "cache"))
        env.pop("WAYLAND_DISPLAY", None)
        result = subprocess.run(["qs", "--path", str(self.root)], env=env,
                                capture_output=True, text=True, timeout=12)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("LOCK_TEST_OK", output, output)
        self.assertNotIn("LOCK_TEST_FAILED", output, output)
        self.assertNotIn("Failed to load configuration", output, output)
        self.assertNotIn("ReferenceError", output, output)
        self.assertNotIn("TypeError", output, output)
        return output

    def test_selection_persists_and_profiles_restore_it(self):
        self.shell('''
            require(SettingsService.lockStyle === "classic", "fresh default");
            SettingsService.set("lockStyle", "mainframe");
            require(SettingsService.snapshot().lockStyle === "mainframe", "profile snapshot");
            finish.start();
        ''')
        settings = self.root / "state/danshell/settings.json"
        self.assertEqual(json.loads(settings.read_text())["lockStyle"], "mainframe")
        self.shell('''
            require(SettingsService.lockStyle === "mainframe", "saved selection after restart");
            const saved = SettingsService.snapshot();
            SettingsService.adopt({lockStyle: "classic"});
            require(SettingsService.lockStyle === "classic", "profile change");
            SettingsService.adopt(saved);
            require(SettingsService.lockStyle === "mainframe", "profile restore");
            finish.start();
        ''')

    def test_unknown_saved_and_selected_styles_use_classic(self):
        (self.root / "state/danshell/settings.json").write_text('{"lockStyle":"uninstalled-style"}')
        self.shell('''
            require(SettingsService.lockStyle === "classic", "invalid saved style");
            SettingsService.set("lockStyle", "unknown");
            require(SettingsService.snapshot().lockStyle === "classic", "invalid selection normalized");
            finish.start();
        ''')

    def test_lock_request_freezes_style_and_motion_without_capture(self):
        self.shell('''
            SettingsService.set("lockStyle", "mainframe");
            LockService.shellQuiet = false;
            LockService.lock();
            require(LockService.activeStyle === "mainframe", "style snapshot");
            require(LockService.exitDuration === 0, "disabled motion deadline");
            SettingsService.set("lockStyle", "classic");
            LockService.lock();
            require(LockService.activeStyle === "mainframe", "pending lock retained style");
            LockService.quietGiveUp.stop();
            LockService.pendingCapture = false;
            require(!LockService.locked, "no actual capture or lock started");
            finish.start();
        ''')

    def test_missing_mainframe_and_invalid_style_load_classic(self):
        self.shell('''
            require(missing.ready && missing.effectiveStyle === "classic", "missing theme fallback");
            require(unknown.ready && unknown.effectiveStyle === "classic", "invalid id fallback");
            missing.claim(); unknown.claim();
            finish.start();
        ''', '''
        LockStyleHost { id: missing; width: 800; height: 600; style: "mainframe"; mainframeSource: "does-not-exist.qml" }
        LockStyleHost { id: unknown; width: 800; height: 600; style: "unknown" }
        ''')

    def test_two_surfaces_share_masked_input_and_clear_after_submission(self):
        self.shell('''
            require(first.ready && second.ready, "mainframe surfaces loaded");
            require(first.effectiveStyle === "mainframe" && second.effectiveStyle === "mainframe", "Mainframe loaded without fallback");
            const firstField = findNamed(first, "mainframePassword");
            const secondField = findNamed(second, "mainframePassword");
            require(firstField && secondField, "both input fields exist");
            firstField.text = "not-a-real-password";
            require(secondField.text === firstField.text, "input mirrored to second display");
            first.claim(); second.claim();
            firstField.accepted();
            require(harness.submittedLength === 19, "submission forwarded through host");
            require(firstField.text === "" && secondField.text === "" && LockService.typed === "", "submitted input cleared on both screens");
            LockService.authenticating = true;
            LockService.failed = true;
            LockService.message = "Wrong password";
            LockService.typed = "";
            LockService.authenticating = false;
            require(LockService.typed === "", "clear across both screens");
            second.destroy();
            first.claim();
            finish.start();
        ''', '''
        property int submittedLength: 0
        LockStyleHost { id: first; width: 1280; height: 720; style: "mainframe"; output: "DP-7"; onSubmitted: password => harness.submittedLength = password.length }
        Component { id: extraScreen; LockStyleHost { width: 800; height: 600; style: "mainframe"; output: "USB-C-9" } }
        property var second: extraScreen.createObject(first)
        ''')

    def test_release_deadline_finishes_without_animation_callbacks(self):
        self.shell('''
            LockService.activeStyle = "mainframe";
            LockService.activeMotion = 0;
            LockService.locked = true; // No WlSessionLock is constructed in this harness.
            LockService.release();
            require(LockService.leaving, "exit began");
            require(LockService.leave.interval === 0, "immediate timer");
            verifyExit.start();
        ''', '''
        Timer { id: verifyExit; interval: 40; onTriggered: {
            if (LockService.locked || LockService.typed !== "") {
                console.error("LOCK_TEST_FAILED release did not finish"); Qt.quit();
            } else finish.start();
        } }
        ''')


@unittest.skipUnless(Path("/usr/lib/qt6/bin/qmltestrunner").is_file(), "Qt 6 QuickTest is required")
class LockPresentationTests(unittest.TestCase):
    def test_presentation_and_style_rules(self):
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        result = subprocess.run(["/usr/lib/qt6/bin/qmltestrunner", "-input", str(ROOT / "tests/qml"), "-o", "-,txt"],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
