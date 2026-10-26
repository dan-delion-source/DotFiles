"""Exercise key deletion with isolated state and a fake compositor command."""
import json
import os
import shutil
import unittest
from unittest.mock import patch

import test_lock_styles as integration


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.fixture = integration.LockStyleIntegrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        root = self.fixture.root
        for folder in ("settings", "components", "bin"):
            (root / folder).mkdir()
        for name in ("PillButton.qml", "SettingDivider.qml"):
            shutil.copy2(integration.ROOT / "components" / name, root / "components" / name)
        shutil.copy2(integration.ROOT / "settings/ShortcutRow.qml", root / "settings/ShortcutRow.qml")
        shutil.copy2(integration.ROOT / "services/ShortcutService.qml", root / "services/ShortcutService.qml")
        (root / "services/HyprlandService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property var binds: [
        {description: "Shell · Open the launcher", combination: "SUPER + Space"},
        {description: "Shell · Open settings", combination: "SUPER + I"}
    ]
    property var modifierNames: [
        {name: "SUPER"}, {name: "CTRL"}, {name: "ALT"}, {name: "SHIFT"}
    ]
    function spell(bind) { return bind.combination }
    function loadBinds() {}
}''')
        (root / "services/Tr.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton { function t(text) { return text } }''')
        (root / "theme/Theme.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property string fontFamily: "Sans Serif"
    property string fontMono: "Monospace"
    property int fontSizeSmall: 12
    property int fontSizeLabel: 11
    property int radiusSmall: 6
    property int radiusPill: 14
    property int durationFast: 0
    property color text: "#ffffff"
    property color textMuted: "#cccccc"
    property color accent: "#88bbff"
    property color accentText: "#111111"
    property color accentHover: "#aaccff"
    property color island: "#202020"
    property color islandSurfaceHover: "#303030"
    property color islandBorder: "#888888"
    property color hairline: "#888888"
    property color yellow: "#ffff88"
    function surfaceIn(window) { return island }
    function surfaceHoverIn(window) { return islandSurfaceHover }
    function borderIn(window) { return islandBorder }
}''')
        # The real service's save/reload path runs, but cannot touch Hyprland.
        command = root / "bin/hyprctl"
        command.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$XDG_STATE_HOME/reloads"\n')
        command.chmod(0o755)
        self.path = patch.dict(os.environ, {"PATH": str(root / "bin") + os.pathsep + os.environ["PATH"]})
        self.path.start()
        self.addCleanup(self.path.stop)

    def run_editor(self, body):
        return self.fixture.shell(body, '''
        function button(text) {
            const pending = [row];
            while (pending.length) {
                const item = pending.pop();
                if (item.text === text && typeof item.clicked === "function") return item;
                pending.push(...(item.children ?? []));
            }
            throw new Error("Missing button: " + text);
        }
        Window { visible: true; width: 640; height: 220
            ShortcutRow { id: row; width: parent.width;
                description: "Shell · Open the launcher"; label: "Launcher" }
        }
        ''', imports='import QtQuick.Window\nimport "./settings"\n')

    def test_delete_persists_unbound_and_can_be_reassigned(self):
        self.run_editor('''
            row.begin();
            const remove = button("Delete"), cancel = button("Cancel"), apply = button("Apply");
            require(remove.enabled, "bound key can be deleted");
            require(remove.x + remove.width <= cancel.x && cancel.x + cancel.width <= apply.x,
                "Delete is immediately left of Cancel and Apply");
            remove.clicked();
            require(row.current === "" && !row.editing, "delete unbinds and closes editor");
            require(ShortcutService.current("Shell · Open settings") === "SUPER + I", "other keys retained");
            row.begin();
            require(!remove.enabled, "delete disabled for unbound key");
            require(row.key === "", "deleted key is not restored by editor");
            finish.start();
        ''')
        root = self.fixture.root
        saved = json.loads((root / "state/danshell/settings.json").read_text())
        self.assertEqual(saved["keys"]["Shell · Open the launcher"], "")
        self.assertIn("Shell · Open the launcher\t\n", (root / "state/danshell/keys.tsv").read_text())
        self.assertIn("reload", (root / "state/reloads").read_text())
        self.run_editor('''
            require(row.current === "", "unbound survives restart despite compositor fallback");
            row.begin();
            row.mods = ["SUPER"]; row.key = "K";
            require(button("Apply").enabled, "unbound action can be reassigned");
            button("Apply").clicked();
            require(row.current === "SUPER + K" && !row.editing, "apply saves replacement");
            finish.start();
        ''')

    def test_cancel_and_unavailable_compositor_preserve_keys(self):
        self.run_editor('''
            row.begin(); row.key = "K";
            button("Cancel").clicked();
            require(row.current === "SUPER + Space" && !row.editing, "cancel leaves binding intact");
            const before = JSON.stringify(SettingsService.keys);
            ShortcutService.rebind("unknown description", "");
            require(JSON.stringify(SettingsService.keys) === before, "unknown action ignored");
            HyprlandService.binds = [];
            ShortcutService.rebind("Shell · Open the launcher", "");
            require(JSON.stringify(SettingsService.keys) === before, "wait for compositor bindings");
            finish.start();
        ''')


if __name__ == "__main__":
    unittest.main()
