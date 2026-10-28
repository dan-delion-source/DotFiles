"""Wallpaper startup ordering, retries and repeated starts without a desktop."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import shutil
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wallpaper_start', ROOT / 'scripts/start-wallpaper.py')
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)


class StartupTests(unittest.TestCase):
    def prepare(self, ready):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        env = dict(WAYLAND_DISPLAY='wayland-test', XDG_RUNTIME_DIR=temporary.name)
        with patch.dict(os.environ, env), patch.object(startup, 'ready', side_effect=ready), \
                patch.object(startup.shutil, 'which', return_value='/bin/awww'), \
                patch.object(startup.subprocess, 'Popen') as daemon, \
                patch.object(startup.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as restore, \
                patch.object(startup.time, 'sleep'):
            result = startup.prepare()
        return result, daemon, restore

    def test_running_daemon_is_reused_and_restore_runs_without_palette_or_scan(self):
        result, daemon, restore = self.prepare([True])
        self.assertEqual(result, 0)
        daemon.assert_not_called()
        self.assertEqual(restore.call_args.args[0][-1], 'restore')

    def test_first_start_waits_for_readiness_and_disables_obsolete_cache(self):
        result, daemon, restore = self.prepare([False, False, True])
        self.assertEqual(result, 0)
        self.assertEqual(daemon.call_args.args[0], ['awww-daemon', '--no-cache'])
        restore.assert_called_once()

    def test_daemon_timeout_is_bounded_and_does_not_run_restore(self):
        with patch.object(startup.time, 'monotonic', side_effect=[10, 13]):
            result, daemon, restore = self.prepare([False, False])
        self.assertEqual(result, 3)
        restore.assert_not_called()

    def test_shell_starts_after_wallpaper_and_survives_preparation_failure(self):
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                scripts = root / 'scripts'
                scripts.mkdir()
                (scripts / 'shell-control.sh').write_text((ROOT / 'scripts/shell-control.sh').read_text())
                (scripts / 'start-wallpaper.py').write_text(
                    'from pathlib import Path\nimport os,sys\n'
                    'Path(os.environ["START_TEST_LOG"]).write_text("wallpaper\\n")\n'
                    f'sys.exit({int(failure)})\n')
                qs = root / 'qs'
                qs.write_text('#!/bin/sh\nprintf "shell\\n" >> "$START_TEST_LOG"\n')
                qs.chmod(0o755)
                env = dict(os.environ, PATH=temporary + os.pathsep + os.environ['PATH'],
                           START_TEST_LOG=str(root / 'events'))
                subprocess.run(['sh', str(scripts / 'shell-control.sh'), 'start'], env=env, check=True)
                self.assertEqual((root / 'events').read_text().splitlines(), ['wallpaper', 'shell'])

    def test_cold_start_cli_waits_for_daemon_then_restores_before_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / 'scripts'
            scripts.mkdir()
            runtime = root / 'runtime'
            runtime.mkdir(mode=0o700)
            for name in ('shell-control.sh', 'start-wallpaper.py'):
                shutil.copy2(ROOT / 'scripts' / name, scripts / name)
            (scripts / 'theme_manager.py').write_text('''import os,sys
from pathlib import Path
assert sys.argv[1:] == ['restore']
with Path(os.environ['START_TEST_LOG']).open('a') as f: f.write('restore\\n')
''')
            (root / 'awww').write_text('''#!/usr/bin/env python3
import os,sys
from pathlib import Path
p = Path(os.environ['XDG_RUNTIME_DIR']) / 'probes'
count = int(p.read_text()) + 1 if p.exists() else 1
p.write_text(str(count))
sys.exit(0 if count >= 3 else 1)
''')
            (root / 'awww-daemon').write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
Path(os.environ['XDG_RUNTIME_DIR'], 'daemon-args').write_text(json.dumps(sys.argv[1:]))
''')
            (root / 'qs').write_text('#!/bin/sh\nprintf "shell\\n" >> "$START_TEST_LOG"\n')
            for name in ('qs', 'awww', 'awww-daemon'):
                (root / name).chmod(0o755)
            env = dict(os.environ, PATH=temporary + os.pathsep + os.environ['PATH'],
                       XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY='isolated-start-test',
                       START_TEST_LOG=str(root / 'events'))
            subprocess.run(['sh', str(scripts / 'shell-control.sh'), 'start'], env=env, check=True, timeout=5)
            self.assertEqual(json.loads((runtime / 'daemon-args').read_text()), ['--no-cache'])
            self.assertGreaterEqual(int((runtime / 'probes').read_text()), 3)
            self.assertEqual((root / 'events').read_text().splitlines(), ['restore', 'shell'])


if __name__ == '__main__':
    unittest.main()
