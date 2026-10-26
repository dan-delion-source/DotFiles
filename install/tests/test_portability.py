"""Native config parsing, fresh-machine flow and standalone uninstall coverage."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('portable_installer', REPO / 'install/installer.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class UninstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='uninstall test ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.config = self.root / 'repo', self.root / 'config'
        for name in installer.CORE_CONFIGS:
            source = self.repo / 'config' / name
            source.mkdir(parents=True)
            (source / 'config.txt').write_text('installed')
            (self.config / name).mkdir(parents=True)
            (self.config / name / 'original.txt').write_text('original')
        self.deployment = installer.Deployment(self.repo, self.config, self.root / 'data', self.root / 'state',
                                              self.root / 'Pictures/Wallpapers')
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.deployment.install()

    def test_keeps_notes_packages_and_imported_wallpapers_by_default(self):
        source = self.root / 'collection'
        source.mkdir()
        (source / 'image.jpg').write_bytes(b'image')
        self.deployment.import_wallpapers(source)
        notes = self.root / 'state/danshell/notes.json'
        notes.parent.mkdir(parents=True)
        notes.write_text('personal notes')
        self.deployment.restore(remove_wallpapers=False)
        self.assertTrue((self.deployment.wallpaper_dir / 'image.jpg').exists())
        self.assertEqual(notes.read_text(), 'personal notes')
        self.assertEqual(self.deployment.load()['entries'], [])
        for name in installer.CORE_CONFIGS:
            self.assertEqual((self.config / name / 'original.txt').read_text(), 'original')
        self.deployment.restore(remove_wallpapers=True)
        self.assertFalse((self.deployment.wallpaper_dir / 'image.jpg').exists())
        self.assertFalse(self.deployment.record.exists())

    def test_preserves_edits_which_were_retained_by_an_update(self):
        (self.config / 'kitty/config.txt').write_text('personal edit')
        (self.repo / 'config/kitty/new.txt').write_text('new source')
        self.deployment.update()
        self.deployment.restore(remove_wallpapers=False)
        kept = list((self.deployment.directory / 'preserved').glob('*/kitty/config.txt'))
        self.assertEqual([p.read_text() for p in kept], ['personal edit'])
        self.assertTrue((self.config / 'kitty/original.txt').exists())

    def test_missing_backup_aborts_before_restoring_any_config(self):
        document = self.deployment.load()
        backup = Path(document['entries'][0]['backup'])
        installer.remove(backup)
        before = installer.fingerprint(self.config)
        with self.assertRaisesRegex(ValueError, 'Backup missing'):
            self.deployment.restore(remove_wallpapers=False)
        self.assertEqual(installer.fingerprint(self.config), before)

    def test_legacy_bundled_wallpapers_are_kept_by_config_uninstall(self):
        legacy = self.root / 'data/wallpapers'
        legacy.mkdir(parents=True)
        (legacy / 'old.jpg').write_bytes(b'old import')
        document = self.deployment.load()
        document['entries'].append({'destination': str(legacy), 'backup': None,
                                    'installed': installer.fingerprint(legacy)})
        installer.save(self.deployment.record, document)
        self.deployment.restore(remove_wallpapers=False)
        self.assertTrue((legacy / 'old.jpg').exists())
        self.assertEqual(len(self.deployment.load()['entries']), 1)
        self.deployment.restore(remove_wallpapers=True)
        self.assertFalse(legacy.exists())

    @unittest.skipIf(os.geteuid() == 0, 'Standalone uninstaller intentionally refuses root')
    def test_standalone_script_works_without_source_configs_or_package_lists(self):
        collection = self.root / 'collection'
        collection.mkdir()
        (collection / 'image.jpg').write_bytes(b'import')
        self.deployment.import_wallpapers(collection)
        distribution = self.root / 'recovery checkout'
        (distribution / 'install').mkdir(parents=True)
        shutil.copy2(REPO / 'install/installer.py', distribution / 'install/installer.py')
        shutil.copy2(REPO / 'uninstall.sh', distribution / 'uninstall.sh')
        env = dict(os.environ, HOME=str(self.root), XDG_CONFIG_HOME=str(self.config),
                   XDG_DATA_HOME=str(self.root / 'data'), XDG_STATE_HOME=str(self.root / 'state'))
        command = ['sh', str(distribution / 'uninstall.sh')]
        before = installer.fingerprint(self.config)
        preview = subprocess.run([*command, '--dry-run'], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        self.assertEqual(installer.fingerprint(self.config), before)
        cancel = subprocess.run(command, input='n\n', env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(cancel.returncode, 0, cancel.stdout + cancel.stderr)
        self.assertEqual(installer.fingerprint(self.config), before)
        result = subprocess.run([*command, '--yes'], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.config / 'hypr/original.txt').exists())
        repeated = subprocess.run([*command, '--yes'], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertTrue((self.deployment.wallpaper_dir / 'image.jpg').exists())
        cleaned = subprocess.run([*command, '--yes', '--remove-wallpapers'], env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(cleaned.returncode, 0, cleaned.stdout + cleaned.stderr)
        self.assertFalse((self.deployment.wallpaper_dir / 'image.jpg').exists())


class FreshMachineTests(unittest.TestCase):
    def test_dependency_check_does_not_reject_user_config_edits(self):
        with patch.object(sys, 'argv', ['install.sh', 'check']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer, 'resolve_dependencies', return_value=[]), \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer, 'wallpaper_health', return_value=('ready', 'daemon responding')), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer.Deployment, 'preflight', side_effect=AssertionError('local edits must not block dependency check')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)

    def test_hyprland_can_be_installed_when_missing(self):
        available = set()
        def which(command):
            return '/usr/bin/' + command if command != 'Hyprland' or command in available else None
        def packages(dependencies):
            self.assertIsNone(which('Hyprland'))
            available.add('Hyprland')
        with patch.object(sys, 'argv', ['install.sh', 'install', '--yes', '--no-wallpapers']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer, 'resolve_dependencies', return_value=[{
                    'id': 'hyprland', 'package': 'hyprland', 'source': 'repository', 'group': 'core',
                    'packages': ['hyprland'], 'commands': ['Hyprland']}]), \
                patch.object(installer, 'verify_aur'), \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer.shutil, 'which', side_effect=which), \
                patch.object(installer.os, 'geteuid', return_value=1000), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer.Deployment, 'preflight'), \
                patch.object(installer, 'install_packages', side_effect=packages) as package_install, \
                patch.object(installer.Deployment, 'install') as deploy, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)
        package_install.assert_called_once()
        deploy.assert_called_once()

    @unittest.skipUnless(shutil.which('Hyprland'), 'Hyprland parser unavailable')
    def test_native_hyprland_parser_accepts_shipped_config(self):
        with patch.object(installer, 'qml_compatibility', return_value=[]):
            self.assertEqual(installer.source_compatibility(REPO), [])

    def test_every_bound_shell_action_is_actually_registered(self):
        shell = (REPO / 'config/quickshell/shell.qml').read_text()
        keys = (REPO / 'config/hypr/modules/keybinds.lua').read_text()
        bound = set(re.findall(r'hl\.dsp\.global\("([^\"]+)"\)', keys))
        registered = set(app + ':' + name for app, name in re.findall(
            r'appid:\s*"([^\"]+)"\s+name:\s*"([^\"]+)"', shell))
        self.assertTrue(bound)
        self.assertEqual(bound - registered, set())

    def test_all_core_packages_are_available_in_configured_repository_databases(self):
        # Uses local repository metadata only; skip on non-Arch test runners.
        if not shutil.which('pacman'):
            self.skipTest('pacman unavailable')
        rows = installer.load_manifest()['features']['core']['dependencies']
        missing = []
        for row in rows:
            if subprocess.run(['pacman', '-Si', row['packages'][0]], capture_output=True).returncode:
                missing.append(row['packages'][0])
        self.assertEqual(missing, [])

    @unittest.skipUnless(Path('/usr/lib/qt6/bin/qsb').exists(), 'Qt shader compiler unavailable')
    def test_full_shipped_config_install_and_uninstall_in_isolated_home(self):
        with tempfile.TemporaryDirectory(prefix='full rice artifact ') as temporary, \
                contextlib.redirect_stdout(io.StringIO()):
            root = Path(temporary)
            deploy = installer.Deployment(REPO, root / 'config', root / 'data', root / 'state',
                                           root / 'Pictures/Wallpapers')
            deploy.install(groups=['core'])
            for source, destination in deploy.targets:
                self.assertTrue(destination.exists(), str(destination))
            self.assertTrue((root / 'config/quickshell/lock/shaders/mainframe-crt.frag.qsb').is_file())
            (root / 'config/kitty/personal.conf').write_text('user-added config')
            deploy.restore(remove_wallpapers=False)
            self.assertFalse((root / 'config/hypr').exists())
            kept = list((deploy.directory / 'preserved').glob('*/kitty/personal.conf'))
            self.assertEqual([p.read_text() for p in kept], ['user-added config'])


class PythonBootstrapTests(unittest.TestCase):
    def run_wrapper(self, arguments, answer=''):
        with tempfile.TemporaryDirectory(prefix='python bootstrap ') as temporary:
            root = Path(temporary)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            log = root / 'actions.log'
            scripts = {
                'id': '#!/bin/sh\necho 1000\n',
                'sudo': '#!/bin/sh\nprintf "sudo %s\\n" "$*" >> "$BOOTSTRAP_LOG"\nexec "$@"\n',
                'pacman': '#!/bin/sh\n/usr/bin/cp "$BOOTSTRAP_TEMPLATE" "$BOOTSTRAP_BIN/python3"\n/usr/bin/chmod +x "$BOOTSTRAP_BIN/python3"\n',
            }
            for name, text in scripts.items():
                (bin_dir / name).write_text(text)
                (bin_dir / name).chmod(0o755)
            (bin_dir / 'dirname').symlink_to(shutil.which('dirname'))
            template = root / 'python-template'
            template.write_text('#!/bin/sh\nprintf "python %s\\n" "$*" >> "$BOOTSTRAP_LOG"\n')
            env = dict(os.environ, PATH=str(bin_dir), BOOTSTRAP_LOG=str(log), BOOTSTRAP_BIN=str(bin_dir),
                       BOOTSTRAP_TEMPLATE=str(template))
            result = subprocess.run(['/bin/sh', str(REPO / 'install.sh'), *arguments], input=answer,
                                    env=env, capture_output=True, text=True, timeout=10)
            return result, log.read_text() if log.exists() else ''

    def test_bootstraps_only_required_python_after_confirmation(self):
        result, actions = self.run_wrapper(['install', '--no-wallpapers'], 'y\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sudo pacman -Syu --needed python', actions)
        self.assertIn('installer.py install --no-wallpapers', actions)

    def test_declined_bootstrap_does_nothing(self):
        result, actions = self.run_wrapper(['install'], 'n\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(actions, '')

    def test_read_only_and_recovery_commands_never_bootstrap(self):
        for arguments in (['check'], ['install', '--dry-run'], ['restore'], ['uninstall'], ['--help']):
            with self.subTest(arguments=arguments):
                result, actions = self.run_wrapper(arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(actions, '')
                self.assertIn('Python is required', result.stderr)


if __name__ == '__main__':
    unittest.main()
