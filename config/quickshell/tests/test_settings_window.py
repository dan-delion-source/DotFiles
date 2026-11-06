"""Settings mapping order and floating-helper targeting regressions."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('float_settings', ROOT / 'scripts/float_settings.py')
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class SettingsHelperTests(unittest.TestCase):
    def test_only_the_requested_shell_process_is_selected(self):
        windows = [dict(title='Settings', mapped=True, **{'class': 'org.danshell'}, pid=10),
                   dict(title='Settings', mapped=True, **{'class': 'org.danshell'}, pid=20)]
        with patch.object(helper.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(windows))):
            self.assertEqual(helper.settings_window(20)['pid'], 20)
            self.assertIsNone(helper.settings_window(30))

    def test_existing_floating_geometry_is_preserved(self):
        with patch.object(helper, 'settings_window', return_value={'floating': True}), patch.object(helper.subprocess, 'run') as run:
            helper.main(20)
            run.assert_not_called()

    def test_tiled_window_is_floated_resized_and_centered_by_address(self):
        with patch.object(helper, 'settings_window', return_value={'floating': False, 'address': '0x123'}), patch.object(helper.subprocess, 'run') as run:
            helper.main(20)
            command = run.call_args.args[0]
            self.assertEqual(command[:2], ['hyprctl', 'eval'])
            self.assertIn('address:0x123', command[2])
            self.assertIn('x=900,y=620', command[2])


@unittest.skipUnless(shutil.which('qs'), 'QuickShell is required')
class SettingsWindowTests(unittest.TestCase):
    def test_delayed_mapping_rapid_reopen_and_resize(self):
        with tempfile.TemporaryDirectory(prefix='settings-window-test-') as directory:
            root = Path(directory)
            for name in ['settings', 'scripts', 'runtime', 'theme']:
                (root / name).mkdir(mode=0o700)
            shutil.copy2(ROOT / 'settings/SettingsWindow.qml', root / 'settings/SettingsWindow.qml')
            (root / 'settings/SettingsPanel.qml').write_text('''import QtQuick
Item { signal closed(); signal panelRequested(string panel) }
''')
            (root / 'theme/qmldir').write_text('module Theme\nsingleton Theme 1.0 Theme.qml\n')
            (root / 'theme/Theme.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { readonly property color background: "#151515" }\n')
            script = root / 'scripts/float_settings.py' 
            script.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(0.18)\n')
            script.chmod(0o755)
            (root / 'shell.qml').write_text('''import QtQuick
import Quickshell
import "./settings"
ShellRoot {
 SettingsWindow { id: win }
 function check(ok, message) { if (!ok) throw new Error(message) }
 function verifyPanel() {
  const loader = win.contentItem.children.find(item => item.objectName === "settingsPanelLoader")
  check(loader && loader.item, "panel was never mounted")
  check(loader.width === win.width && loader.height === win.height, "loader has stale geometry")
  check(loader.item.width === win.width && loader.item.height === win.height, "page has stale geometry")
 }
 Timer {
  interval: 25; running: true; repeat: true
  property int step: 0
  property int ticks: 0
  property int cycles: 0
  onTriggered: {
   try {
    ticks++
    if (ticks > 500) throw new Error("lifecycle timed out")
    if (step === 0) {
     win.open(); check(!win.contentReady, "page mounted before helper")
     const loader = win.contentItem.children.find(item => item.objectName === "settingsPanelLoader")
     check(loader && !loader.active && loader.item === null, "animated content exists before floating finishes")
     step = 1
    }
    else if (step === 1) {
     // Close while the previous mapping helper is still running, then reopen.
     win.close(); win.open(); check(!win.contentReady, "stale page on rapid reopen"); step = 2
    } else if (step === 2 && win.contentReady) {
     verifyPanel()
     win.minimumSize = Qt.size(800, 560); win.maximumSize = Qt.size(800, 560)
     step = 3
    } else if (step === 3) {
     verifyPanel(); win.close(); check(!win.contentReady, "ready flag survived close")
     cycles++
     if (cycles >= 12) { console.log("SETTINGS_WINDOW_PASS", cycles); Qt.quit() }
     else step = 0
    }
   } catch (error) { console.error("SETTINGS_WINDOW_FAIL", error); Qt.quit() }
  }
 }
}
''')
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_RUNTIME_DIR=str(root / 'runtime'))
            result = subprocess.run(['qs', '--path', str(root)], env=env, capture_output=True, text=True, timeout=25)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('SETTINGS_WINDOW_PASS 12', output)
            self.assertNotIn('SETTINGS_WINDOW_FAIL', output)
