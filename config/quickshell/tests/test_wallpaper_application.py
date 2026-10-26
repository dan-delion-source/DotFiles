"""Wallpaper failures must not be persisted as successful selections."""
import contextlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import theme_manager


class WallpaperApplicationTests(unittest.TestCase):
    def test_unreachable_daemon_preserves_selection_and_palette(self):
        self.failed_application([subprocess.CompletedProcess([], 1, '', 'Connection refused')])

    def test_failed_image_command_preserves_selection_and_palette(self):
        self.failed_application([subprocess.CompletedProcess([], 0, 'ready', ''),
                                 subprocess.CompletedProcess([], 1, '', 'Cannot decode image')])

    def test_missing_executable_preserves_selection_and_palette(self):
        self.failed_application(FileNotFoundError('awww'))

    def test_timeout_preserves_selection_and_palette(self):
        self.failed_application(subprocess.TimeoutExpired('awww', 5))

    def failed_application(self, results):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / 'new image.png'
            image.write_bytes(b'picture')
            with patch.object(theme_manager.subprocess, 'run', side_effect=results), \
                    patch.object(theme_manager, 'save_state') as save, \
                    patch.object(theme_manager, 'extract_colors') as palette, \
                    patch.object(theme_manager, 'link_current_wallpaper') as link, \
                    patch.object(theme_manager, 'stop_motion') as stop, \
                    contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertFalse(theme_manager.set_wallpaper(str(image)))
            for mutation in (save, palette, link, stop):
                mutation.assert_not_called()
            self.assertIn('awww-daemon', errors.getvalue())

    def test_success_saves_selection_and_updates_palette(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / 'new image.png'
            image.write_bytes(b'picture')
            with patch.object(theme_manager.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as command, \
                    patch.object(theme_manager, 'load_state', return_value={'activeTheme': 'adaptive'}), \
                    patch.object(theme_manager, 'save_state') as save, \
                    patch.object(theme_manager, 'extract_colors') as palette, \
                    patch.object(theme_manager, 'link_current_wallpaper'), \
                    patch.object(theme_manager, 'stop_motion'):
                self.assertTrue(theme_manager.set_wallpaper(str(image), 'invalid-transition'))
            self.assertEqual(command.call_args_list[0].args[0], ['awww', 'query'])
            self.assertIn('wipe', command.call_args_list[1].args[0])
            self.assertEqual(save.call_args.args[0]['currentWallpaper'], str(image))
            palette.assert_called_once_with(str(image))

    def test_restore_reports_failed_output_application(self):
        results = [subprocess.CompletedProcess([], 0, ': DP-1: 1920x1080, scale: 1, currently displaying: color: 000000\n', ''),
                   subprocess.CompletedProcess([], 1, '', 'Connection lost')]
        with patch.object(theme_manager.shutil, 'which', return_value='/usr/bin/awww'), \
                patch.object(theme_manager.subprocess, 'run', side_effect=results), \
                patch.object(theme_manager, 'get_current_motion', return_value=''), \
                patch.object(theme_manager, 'get_current_wallpaper', return_value='/wall.png'), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(theme_manager.restore_wallpaper(), 1)
        self.assertIn('Connection lost', errors.getvalue())

    def test_restore_retries_unavailable_daemon(self):
        with patch.object(theme_manager.shutil, 'which', return_value='/usr/bin/awww'), \
                patch.object(theme_manager.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Connection refused')), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(theme_manager.restore_wallpaper(), 3)

    def test_motion_without_player_does_not_change_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            video = Path(temporary) / 'movie.mp4'
            video.write_bytes(b'video')
            with patch.object(theme_manager, 'run_awww', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                    patch.object(theme_manager.shutil, 'which', return_value=None), \
                    patch.object(theme_manager, 'save_state') as save, \
                    patch.object(theme_manager, 'stop_motion') as stop, \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(theme_manager.set_wallpaper(str(video)))
            save.assert_not_called()
            stop.assert_not_called()


@unittest.skipUnless(shutil.which('qs'), 'QuickShell is required')
class WallpaperPickerIntegrationTests(unittest.TestCase):
    def test_failed_choice_stays_unselected_then_success_emits_once(self):
        with tempfile.TemporaryDirectory(prefix='wallpaper-picker-') as temporary:
            root = Path(temporary)
            for folder in ('services', 'scripts', 'runtime', 'state', 'cache', 'data'):
                (root / folder).mkdir(mode=0o700)
            shutil.copy2(SCRIPTS.parent / 'services/WallpaperService.qml', root / 'services/WallpaperService.qml')
            (root / 'services/SettingsService.qml').write_text("""pragma Singleton
import QtQuick
QtObject { readonly property string wallpaperTransition: "wipe" }
""")
            (root / 'state.json').write_text(json.dumps({'currentWallpaper': 'old.png', 'currentMotion': ''}))
            backend = root / 'scripts/theme_manager.py'
            backend.write_text("#!/usr/bin/env python3\n" + """
import json
from pathlib import Path
import sys
state = Path(__file__).parents[1] / 'state.json'
action = sys.argv[1]
if action == 'get-state':
    print(state.read_text())
elif action == 'list-library':
    print(json.dumps({'wallpapers': [], 'animated': []}))
elif action == 'set-wallpaper':
    if sys.argv[2] == 'bad.png':
        sys.stderr.write('Daemon unavailable; run awww-daemon\\n')
        sys.exit(1)
    state.write_text(json.dumps({'currentWallpaper': sys.argv[2], 'currentMotion': ''}))
""")
            backend.chmod(0o755)
            (root / 'scripts/watch_wallpapers.py').write_text('import time; time.sleep(10)')
            (root / 'shell.qml').write_text("""import QtQuick
import Quickshell
import "./services"
ShellRoot {
    id: harness
    property int phase: 0
    property int appliedCount: 0
    Connections {
        target: WallpaperService
        function onApplied(path: string): void { harness.appliedCount += 1 }
    }
    Timer {
        interval: 25; running: true; repeat: true
        onTriggered: {
            try {
                if (harness.phase === 0 && WallpaperService.currentWallpaper === "old.png") {
                    WallpaperService.apply("bad.png")
                    if (WallpaperService.chosen !== "old.png") throw new Error("optimistic selection")
                    harness.phase = 1
                } else if (harness.phase === 1 && WallpaperService.error !== "") {
                    if (WallpaperService.chosen !== "old.png" || harness.appliedCount !== 0)
                        throw new Error("failed choice committed")
                    if (WallpaperService.applyProcess.running) return
                    WallpaperService.apply("new.png")
                    harness.phase = 2
                } else if (harness.phase === 2 && WallpaperService.chosen === "new.png") {
                    if (harness.appliedCount !== 1 || WallpaperService.error !== "")
                        throw new Error("successful choice not committed once")
                    console.log("WALLPAPER_PICKER_OK")
                    Qt.quit()
                }
            } catch (error) { console.error("WALLPAPER_PICKER_FAILED", error); Qt.quit() }
        }
    }
    Timer { interval: 5000; running: true; onTriggered: { console.error("WALLPAPER_PICKER_FAILED timeout"); Qt.quit() } }
}
""")
            env = dict(os.environ, HOME=str(root), QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       XDG_RUNTIME_DIR=str(root / 'runtime'), XDG_STATE_HOME=str(root / 'state'),
                       XDG_DATA_HOME=str(root / 'data'), XDG_CACHE_HOME=str(root / 'cache'))
            env.pop('WAYLAND_DISPLAY', None)
            env.pop('HYPRLAND_INSTANCE_SIGNATURE', None)
            result = subprocess.run(['qs', '--path', str(root)], env=env, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('WALLPAPER_PICKER_OK', output)
            self.assertNotIn('WALLPAPER_PICKER_FAILED', output)
            self.assertNotIn('ReferenceError', output)
            self.assertNotIn('TypeError', output)


if __name__ == '__main__':
    unittest.main()
