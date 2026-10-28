"""Regression tests for interface churn and config-specific process control."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('shell_stats', ROOT / 'scripts/stats.py')
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


class NetworkTests(unittest.TestCase):
    def rates(self, before, after):
        with patch.object(stats, 'read', return_value=''), patch.object(stats, 'memory', return_value={}):
            return stats.report((10, [], before), (12, [], after),
                                {'disks': [], 'temperature': None})['network']

    def test_rates_and_idle(self):
        self.assertEqual(self.rates({'eth0': (100, 50)}, {'eth0': (2100, 550)}),
                         {'down': 1000, 'up': 250})
        self.assertEqual(self.rates({'eth0': (100, 50)}, {'eth0': (100, 50)}),
                         {'down': 0, 'up': 0})

    def test_new_disappearing_and_reset_interfaces(self):
        self.assertEqual(self.rates({'eth0': (100, 50), 'tun0': (50000, 80000)},
                                    {'eth0': (500, 150), 'wlan0': (900000, 900000)}),
                         {'down': 200, 'up': 50})
        self.assertEqual(self.rates({'eth0': (9999, 9999)}, {'eth0': (10, 20)}),
                         {'down': 0, 'up': 0})
        self.assertEqual(self.rates({}, {}), {'down': 0, 'up': 0})

    def test_multiple_interfaces(self):
        self.assertEqual(self.rates({'a': (0, 0), 'b': (0, 0)},
                                    {'a': (200, 100), 'b': (400, 300)}),
                         {'down': 300, 'up': 200})

    def test_loopback_excluded(self):
        sample = 'header\nheader\n lo: 999 0 0 0 0 0 0 0 999\n eth0: 100 0 0 0 0 0 0 0 200\n'
        with patch.object(stats, 'read', return_value=sample):
            self.assertEqual(stats.network_bytes(), {'eth0': (100, 200)})


class ProcessIsolationTests(unittest.TestCase):
    def test_control_commands_target_this_checkout(self):
        with tempfile.TemporaryDirectory(prefix='danshell-control-') as folder:
            tmp = Path(folder)
            qs = tmp / 'qs'
            qs.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                          'with open(os.environ["SHELL_TEST_LOG"],"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                          'sys.exit(1 if sys.argv[1]=="ipc" and os.environ.get("FAIL_IPC")=="1" else 0)\n')
            qs.chmod(0o755)
            env = dict(os.environ, PATH=str(tmp) + os.pathsep + os.environ['PATH'],
                       SHELL_TEST_LOG=str(tmp / 'calls'))
            # Keep startup preparation isolated from the real desktop too.
            scripts = tmp / 'scripts'
            scripts.mkdir()
            (scripts / 'shell-control.sh').write_text((ROOT / 'scripts/shell-control.sh').read_text())
            (scripts / 'start-wallpaper.py').write_text('pass\n')
            command = ['sh', str(scripts / 'shell-control.sh')]
            for action in ['start', 'restart', 'stop']:
                subprocess.run(command + [action], env=env, check=True)
            subprocess.run(command + ['restart'], env=dict(env, FAIL_IPC='1'), check=True)
            calls = [json.loads(line) for line in (tmp / 'calls').read_text().splitlines()]
            self.assertEqual(calls, [
                ['--path', str(tmp), '--no-duplicate', '--daemonize'],
                ['ipc', '--path', str(tmp), 'call', 'shell', 'reload'],
                ['kill', '--path', str(tmp)],
                ['ipc', '--path', str(tmp), 'call', 'shell', 'reload'],
                ['--path', str(tmp), '--no-duplicate', '--daemonize']])


if __name__ == '__main__':
    unittest.main()
