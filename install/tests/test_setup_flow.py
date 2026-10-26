"""Installer flow and wallpaper ownership regressions; no live changes."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('setup_installer', Path(__file__).parents[1] / 'installer.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class WallpaperImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wallpaper install ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        repo = self.root / 'repo'
        for name in ('hypr', 'quickshell', 'kitty', 'fastfetch', 'matugen'):
            (repo / 'config' / name).mkdir(parents=True)
        self.deployment = installer.Deployment(repo, self.root / 'config', self.root / 'data',
                                              self.root / 'state', self.root / 'Pictures/Wallpapers')
        self.library = self.deployment.wallpaper_dir
        self.source = self.root / 'collection/wallpapers'
        self.source.mkdir(parents=True)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_no_bundled_wallpapers_needed(self):
        self.deployment.preflight()
        self.deployment.install()
        self.assertFalse((self.root / 'data/wallpapers').exists())
        self.assertFalse(self.library.exists())

    def test_import_preserves_conflicts_and_restore_preserves_edits(self):
        self.library.mkdir(parents=True)
        (self.library / 'existing.png').write_bytes(b'personal')
        (self.library / 'same.jpg').write_bytes(b'same')
        for name, data in [('existing.png', b'external'), ('same.jpg', b'same'),
                           ('new.png', b'new'), ('edited.jpg', b'original'),
                           ('motion.mp4', b'video'), ('README.md', b'not media')]:
            (self.source / name).write_bytes(data)
        counts = self.deployment.import_wallpapers(self.source)
        self.assertEqual(counts, {'added': 3, 'identical': 1, 'conflicts': 1})
        self.assertEqual((self.library / 'existing.png').read_bytes(), b'personal')
        self.assertTrue((self.library / 'animated/motion.mp4').exists())
        self.assertFalse((self.library / 'README.md').exists())
        record = self.deployment.record.read_bytes()
        self.deployment.import_wallpapers(self.source)
        self.assertEqual(record, self.deployment.record.read_bytes())
        (self.library / 'edited.jpg').write_bytes(b'edit')
        before = installer.fingerprint(self.root)
        self.deployment.restore(dry_run=True)
        self.assertEqual(before, installer.fingerprint(self.root))
        self.deployment.restore()
        self.assertEqual(sorted(p.name for p in self.library.glob('*') if p.is_file()),
                         ['edited.jpg', 'existing.png', 'same.jpg'])
        self.assertFalse((self.library / 'animated/motion.mp4').exists())

    def test_symlinked_media_and_destination_are_not_followed(self):
        (self.root / 'outside.png').write_bytes(b'private')
        (self.source / 'link.png').symlink_to(self.root / 'outside.png')
        self.deployment.import_wallpapers(self.source)
        self.assertFalse((self.library / 'link.png').exists())
        (self.source / 'motion.gif').write_bytes(b'motion')
        self.library.mkdir(parents=True, exist_ok=True)
        outside = self.root / 'outside'
        outside.mkdir()
        (self.library / 'animated').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlinked parent'):
            self.deployment.import_wallpapers(self.source)
        self.assertEqual(list(outside.iterdir()), [])

    def test_restore_keeps_replaced_symlink(self):
        (self.source / 'new.png').write_bytes(b'new')
        self.deployment.import_wallpapers(self.source)
        path = self.library / 'new.png'
        path.unlink()
        path.symlink_to(self.root / 'elsewhere')
        self.deployment.restore()
        self.assertTrue(path.is_symlink())

    def test_download_failure_does_not_touch_library(self):
        with patch.object(installer.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'git')), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertFalse(self.deployment.download_wallpapers())
        self.assertFalse(self.library.exists())
        self.assertIn('./install.sh wallpapers', errors.getvalue())

    def test_clone_uses_only_media_subdirectory(self):
        def clone(args, **kwargs):
            self.assertIn('--depth', args)
            dest = Path(args[-1])
            (dest / 'wallpapers').mkdir(parents=True)
            (dest / 'wallpapers/new.jpg').write_bytes(b'picture')
            (dest / 'README.md').write_text('metadata')
            return subprocess.CompletedProcess(args, 0)
        with patch.object(installer.subprocess, 'run', side_effect=clone):
            self.assertTrue(self.deployment.download_wallpapers())
        self.assertEqual([p.name for p in self.library.iterdir()], ['new.jpg'])

    def test_legacy_wallpaper_backup_remains_restorable(self):
        old = self.root / 'data/wallpapers'
        old.mkdir(parents=True)
        (old / 'new.jpg').write_bytes(b'installed')
        backup = self.deployment.directory / 'backups/old/5'
        backup.mkdir(parents=True)
        (backup / 'personal.jpg').write_bytes(b'original')
        installer.save(self.deployment.record, {'schema': 1, 'entries': [
            {'destination': str(old), 'backup': str(backup), 'installed': installer.fingerprint(old)}]})
        self.deployment.preflight()
        self.deployment.restore()
        self.assertEqual([p.name for p in old.iterdir()], ['personal.jpg'])

    def test_record_cannot_escape_wallpaper_directory(self):
        installer.save(self.deployment.record, {'schema': 1, 'entries': [], 'wallpapers': {
            'directory': str(self.library), 'files': {'../outside.png': 'bad'}}})
        with self.assertRaisesRegex(ValueError, 'Invalid wallpaper path'):
            self.deployment.load()


class SetupFlowTests(unittest.TestCase):
    def test_manifest_keeps_core_and_optional_packages_separate(self):
        manifest = installer.load_manifest()
        core = {p for d in manifest['features']['core']['dependencies'] for p in d['packages']}
        animated = {p for d in manifest['features']['animated']['dependencies'] for p in d['packages']}
        self.assertIn('libpulse', core)
        self.assertIn('gtk3', core)
        self.assertIn('qt6-shadertools', core)
        self.assertNotIn('ffmpeg', core)
        self.assertIn('ffmpeg', animated)
        self.assertNotIn('git', core)
        self.assertNotIn('spotify', core)
        self.assertEqual(installer.selection(manifest, []), ['core'])
        matugen = next(d for d in manifest['features']['core']['dependencies'] if d['id'] == 'matugen')
        self.assertEqual(matugen['packages'], ['matugen'])

    def test_invalid_or_missing_package_entry_fails_before_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / 'dependencies.json'
            metadata.write_text(json.dumps({'features': {'core': {'dependencies': [{'id': 'tool', 'commands': []}]}}}))
            (root / 'aur.txt').write_text('')
            for text, message in [('# group: core\n$(bad)\n', 'Invalid package'),
                                  ('# group: core\n', 'Missing package'),
                                  ('# group: core\ntool\ntool\n', 'Duplicate package')]:
                (root / 'pacman.txt').write_text(text)
                with self.assertRaisesRegex(ValueError, message):
                    installer.load_manifest(metadata, root)

    def test_menu_reprompts_and_exit_is_harmless(self):
        with patch('builtins.input', side_effect=['wrong', '5']), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(installer.menu())

    def test_missing_helper_cannot_install_repository_packages_first(self):
        dependencies = [{'source': 'repository', 'package': 'tool'}, {'source': 'AUR', 'package': 'aur-tool'}]
        with patch.object(installer.shutil, 'which', return_value=None), \
                patch.object(installer.subprocess, 'run') as mutation:
            with self.assertRaisesRegex(ValueError, 'existing paru/yay'):
                installer.install_packages(dependencies)
        mutation.assert_not_called()

    def test_no_colour_in_plain_output(self):
        with patch.dict(os.environ, {'NO_COLOR': ''}), contextlib.redirect_stdout(io.StringIO()) as output:
            installer.Terminal().banner()
        self.assertNotIn('\033', output.getvalue())

    def test_wallpaper_flags_require_explicit_opt_in(self):
        self.assertIsNone(installer.parser().parse_args(['install', '--yes']).wallpapers)
        self.assertTrue(installer.parser().parse_args(['install', '--wallpapers']).wallpapers)
        self.assertFalse(installer.parser().parse_args(['install', '--no-wallpapers']).wallpapers)

    def test_health_distinguishes_missing_outside_and_unavailable(self):
        with patch.object(installer.shutil, 'which', return_value=None):
            self.assertEqual(installer.wallpaper_health()[0], 'missing')
        with patch.object(installer.shutil, 'which', return_value='/usr/bin/awww'), \
                patch.dict(os.environ, {}, clear=True):
            self.assertEqual(installer.wallpaper_health()[0], 'outside-session')
        with patch.object(installer.shutil, 'which', return_value='/usr/bin/awww'), \
                patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-1'}), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Connection refused')):
            state, detail = installer.wallpaper_health()
        self.assertEqual(state, 'unavailable')
        self.assertIn('awww-daemon', detail)

    def test_dry_run_never_calls_package_install_or_download(self):
        with patch.object(sys, 'argv', ['install.sh', 'install', '--dry-run', '--wallpapers']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer, 'resolve_dependencies', return_value=[]), \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer.Deployment, 'preflight'), \
                patch.object(installer, 'install_packages') as packages, \
                patch.object(installer.Deployment, 'download_wallpapers') as download, \
                patch('builtins.input', side_effect=AssertionError('dry run prompted')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)
        packages.assert_not_called()
        download.assert_not_called()

    def test_cancel_does_not_call_package_install_or_deploy(self):
        with patch.object(sys, 'argv', ['install.sh', 'install', '--groups', 'animated', '--no-wallpapers']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer, 'resolve_dependencies', return_value=[]), \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer.os, 'geteuid', return_value=1000), \
                patch.object(installer.shutil, 'which', return_value='/usr/bin/tool'), \
                patch.object(installer.Deployment, 'preflight'), \
                patch.object(installer, 'install_packages') as packages, \
                patch.object(installer.Deployment, 'install') as deploy, \
                patch('builtins.input', return_value='n'), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)
        packages.assert_not_called()
        deploy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
