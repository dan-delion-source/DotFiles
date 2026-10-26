"""New config entries must work for fresh installs and existing deployments."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('discovery_installer', Path(__file__).parents[1] / 'installer.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class ConfigDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='config discovery ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.config = self.root / 'repo', self.root / 'config'
        for name in installer.CORE_CONFIGS:
            directory = self.repo / 'config' / name
            directory.mkdir(parents=True)
            (directory / 'config.txt').write_text('original source')
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.refresh()

    def refresh(self):
        self.deploy = installer.Deployment(self.repo, self.config, self.root / 'data',
                                           self.root / 'state', self.root / 'Pictures/Wallpapers')

    def add_source(self, name, contents='incoming'):
        path = self.repo / 'config' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
        return path

    def test_all_new_directories_install_and_restore(self):
        for path in ('gtk-3.0/settings.ini', 'gtk-4.0/settings.ini', 'nvim/init.lua', 'yazi/yazi.toml'):
            self.add_source(path)
        (self.config / 'nvim').mkdir(parents=True)
        (self.config / 'nvim/personal.lua').write_text('original editor')
        self.refresh()
        self.deploy.install()
        for name in ('gtk-3.0', 'gtk-4.0', 'nvim', 'yazi'):
            self.assertTrue((self.config / name).is_dir())
        self.deploy.restore()
        self.assertEqual((self.config / 'nvim/personal.lua').read_text(), 'original editor')
        self.assertFalse((self.config / 'yazi').exists())

    def test_new_directory_is_added_by_update_to_old_install(self):
        self.deploy.install()
        self.add_source('nvim/init.lua')
        self.add_source('nvim/lua/options.lua')
        self.refresh()
        before = installer.fingerprint(self.root)
        plans = self.deploy.plan_update()
        self.deploy.preview_update(plans)
        self.assertEqual(before, installer.fingerprint(self.root))
        self.assertEqual(self.deploy.update(plans), 0)
        self.assertEqual((self.config / 'nvim/init.lua').read_text(), 'incoming')
        entry = next(e for e in self.deploy.load()['entries'] if e['destination'] == str(self.config / 'nvim'))
        self.assertIsNone(entry['backup'])
        self.assertIn('lua/options.lua', entry['files'])
        self.deploy.restore()
        self.assertFalse((self.config / 'nvim').exists())

    def test_new_directory_merges_without_losing_existing_app_data(self):
        self.deploy.install()
        self.add_source('gtk-3.0/settings.ini', 'upstream settings')
        self.add_source('gtk-3.0/new.ini', 'new defaults')
        local = self.config / 'gtk-3.0'
        local.mkdir()
        (local / 'settings.ini').write_text('personal settings')
        (local / 'gtk.css').write_text('generated colours')
        self.refresh()
        self.assertEqual(self.deploy.update(), 1)
        self.assertEqual((local / 'settings.ini').read_text(), 'personal settings')
        self.assertEqual((local / 'gtk.css').read_text(), 'generated colours')
        self.assertEqual((local / 'new.ini').read_text(), 'new defaults')
        entry = next(e for e in self.deploy.load()['entries'] if e['destination'] == str(local))
        original_backup = entry['backup']
        self.assertEqual((Path(original_backup) / 'settings.ini').read_text(), 'personal settings')
        self.assertEqual(self.deploy.update(), 1)
        entry = next(e for e in self.deploy.load()['entries'] if e['destination'] == str(local))
        self.assertEqual(entry['backup'], original_backup)
        self.deploy.restore()
        self.assertEqual((local / 'gtk.css').read_text(), 'generated colours')
        self.assertFalse((local / 'new.ini').exists())

    def test_top_level_config_file_installs_updates_and_restores(self):
        source = self.add_source('application.conf', 'version one')
        self.config.mkdir()
        (self.config / 'application.conf').write_text('original')
        self.refresh()
        self.deploy.install()
        source.write_text('version two')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.config / 'application.conf').read_text(), 'version two')
        self.deploy.restore()
        self.assertEqual((self.config / 'application.conf').read_text(), 'original')

    def test_update_can_add_top_level_file(self):
        self.deploy.install()
        self.add_source('application.conf')
        self.refresh()
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.config / 'application.conf').read_text(), 'incoming')
        self.deploy.restore()
        self.assertFalse((self.config / 'application.conf').exists())

    def test_new_conflicting_top_level_file_is_backed_up_and_kept(self):
        self.deploy.install()
        self.add_source('application.conf')
        (self.config / 'application.conf').write_text('personal')
        self.refresh()
        self.assertEqual(self.deploy.update(), 1)
        self.assertEqual((self.config / 'application.conf').read_text(), 'personal')
        self.deploy.restore()
        self.assertEqual((self.config / 'application.conf').read_text(), 'personal')

    def test_removed_source_target_remains_restorable(self):
        source = self.add_source('application.conf')
        self.refresh()
        self.deploy.install()
        source.unlink()
        self.refresh()
        self.assertEqual(self.deploy.update(), 0)
        self.assertTrue((self.config / 'application.conf').exists())
        self.deploy.restore()
        self.assertFalse((self.config / 'application.conf').exists())

    def test_new_source_root_symlink_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.repo / 'config/extra').symlink_to(outside)
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'symlinked source'):
            self.deploy.preflight()
        self.assertFalse(self.deploy.record.exists())

    def test_new_live_root_symlink_is_kept_without_following(self):
        self.deploy.install()
        self.add_source('nvim/init.lua')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'init.lua').write_text('private target')
        (self.config / 'nvim').symlink_to(outside)
        self.refresh()
        self.assertEqual(self.deploy.update(), 1)
        self.assertTrue((self.config / 'nvim').is_symlink())
        self.assertEqual((outside / 'init.lua').read_text(), 'private target')
        self.deploy.restore()
        self.assertTrue((self.config / 'nvim').is_symlink())

    def test_metadata_does_not_become_app_configuration(self):
        self.add_source('README.md')
        self.add_source('AGENTS.md')
        self.add_source('__pycache__/example.pyc')
        self.refresh()
        self.assertEqual([s.name for s, _ in self.deploy.targets], list(installer.CORE_CONFIGS))

    def test_record_cannot_restore_parent_of_config_root(self):
        installer.save(self.deploy.record, {'entries': [{'destination': str(self.config / '..'),
                                                        'backup': None, 'installed': None}]})
        with self.assertRaisesRegex(ValueError, 'different XDG'):
            self.deploy.load()


if __name__ == '__main__':
    unittest.main()
