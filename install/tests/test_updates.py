"""Updates use temporary configurations and never touch the running desktop."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('update_installer', Path(__file__).parents[1] / 'installer.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='config update ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.config = self.root / 'repo', self.root / 'config'
        for name in ('hypr', 'quickshell', 'kitty', 'fastfetch', 'matugen'):
            source = self.repo / 'config' / name
            source.mkdir(parents=True)
            (source / 'config.txt').write_text('version one')
        (self.config / 'hypr').mkdir(parents=True)
        (self.config / 'hypr/original.txt').write_text('before initial installation')
        self.deploy = installer.Deployment(self.repo, self.config, self.root / 'data',
                                           self.root / 'state', self.root / 'Pictures/Wallpapers')
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.deploy.install(groups=['core', 'animated'])
        self.source = self.repo / 'config/hypr'
        self.live = self.config / 'hypr'

    def legacy_record(self):
        document = self.deploy.load()
        for entry in document['entries']:
            entry.pop('files', None)
            entry.pop('local_changes', None)
        installer.save(self.deploy.record, document)

    def entry(self):
        return next(e for e in self.deploy.load()['entries'] if e['destination'] == str(self.live))

    def test_updates_unchanged_files_adds_files_and_retains_original_backup(self):
        original_backup = self.entry()['backup']
        (self.source / 'config.txt').write_text('version two')
        (self.source / 'new.txt').write_text('new file')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'config.txt').read_text(), 'version two')
        self.assertEqual((self.live / 'new.txt').read_text(), 'new file')
        self.assertEqual(self.entry()['backup'], original_backup)
        previous = list((self.deploy.directory / 'updates').glob('*/before/hypr/config.txt'))
        self.assertEqual([p.read_text() for p in previous], ['version one'])
        self.deploy.restore()
        self.assertEqual((self.live / 'original.txt').read_text(), 'before initial installation')

    def test_local_only_changes_survive_upstream_updates_elsewhere(self):
        (self.live / 'config.txt').write_text('personal edit')
        (self.live / 'user.txt').write_text('private addition')
        (self.source / 'new.txt').write_text('upstream addition')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'config.txt').read_text(), 'personal edit')
        self.assertEqual((self.live / 'user.txt').read_text(), 'private addition')
        self.assertTrue((self.live / 'new.txt').is_file())
        self.assertTrue(self.entry()['local_changes'])
        with self.assertRaisesRegex(ValueError, 'Use update'):
            self.deploy.preflight()

    def test_conflict_is_preserved_reported_again_and_resolves_on_manual_merge(self):
        (self.live / 'config.txt').write_text('personal')
        (self.source / 'config.txt').write_text('upstream')
        self.assertEqual(self.deploy.update(), 1)
        self.assertEqual((self.live / 'config.txt').read_text(), 'personal')
        reviews = list((self.deploy.directory / 'updates').glob('*/incoming/hypr/config.txt'))
        self.assertEqual([p.read_text() for p in reviews], ['upstream'])
        self.assertEqual(self.deploy.update(), 1)
        (self.live / 'config.txt').write_text('upstream')
        self.assertEqual(self.deploy.update(), 0)
        self.assertFalse(self.entry()['local_changes'])
        (self.source / 'config.txt').write_text('upstream next')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'config.txt').read_text(), 'upstream next')

    def test_upstream_deletions_preserve_locally_edited_files(self):
        (self.source / 'remove.txt').write_text('old')
        self.deploy.update()
        (self.source / 'remove.txt').unlink()
        (self.live / 'config.txt').write_text('personal')
        (self.source / 'config.txt').unlink()
        self.assertEqual(self.deploy.update(), 1)
        self.assertFalse((self.live / 'remove.txt').exists())
        self.assertEqual((self.live / 'config.txt').read_text(), 'personal')
        notes = list((self.deploy.directory / 'updates').glob('*/conflicts/hypr.json'))
        self.assertEqual(json.loads(notes[-1].read_text())['paths'], ['config.txt'])

    def test_local_file_deletion_is_not_reintroduced(self):
        (self.live / 'config.txt').unlink()
        (self.source / 'new.txt').write_text('new')
        self.assertEqual(self.deploy.update(), 0)
        self.assertFalse((self.live / 'config.txt').exists())
        (self.source / 'config.txt').write_text('upstream changed deleted file')
        self.assertEqual(self.deploy.update(), 1)
        self.assertFalse((self.live / 'config.txt').exists())

    def test_removed_directory_with_local_additions_is_preserved(self):
        (self.source / 'modules').mkdir()
        (self.source / 'modules/owned.txt').write_text('owned')
        self.deploy.update()
        (self.live / 'modules/personal.txt').write_text('personal')
        installer.remove(self.source / 'modules')
        self.assertEqual(self.deploy.update(), 1)
        self.assertEqual((self.live / 'modules/personal.txt').read_text(), 'personal')
        self.assertTrue((self.live / 'modules/owned.txt').exists())

    def test_clean_directory_to_file_and_back(self):
        (self.source / 'node').mkdir()
        (self.source / 'node/child.txt').write_text('child')
        self.deploy.update()
        installer.remove(self.source / 'node')
        (self.source / 'node').write_text('now a file')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'node').read_text(), 'now a file')
        (self.source / 'node').unlink()
        (self.source / 'node').mkdir()
        (self.source / 'node/new.txt').write_text('new child')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'node/new.txt').read_text(), 'new child')

    def test_local_directory_symlink_is_never_followed(self):
        (self.source / 'modules').mkdir()
        (self.source / 'modules/owned.txt').write_text('original')
        self.deploy.update()
        installer.remove(self.live / 'modules')
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'owned.txt').write_text('private target')
        (self.live / 'modules').symlink_to(outside)
        (self.source / 'modules/owned.txt').write_text('upstream')
        self.assertEqual(self.deploy.update(), 1)
        self.assertTrue((self.live / 'modules').is_symlink())
        self.assertEqual((outside / 'owned.txt').read_text(), 'private target')

    def test_locally_deleted_directory_is_preserved_as_missing(self):
        (self.source / 'modules').mkdir()
        (self.source / 'modules/owned.txt').write_text('original')
        self.deploy.update()
        installer.remove(self.live / 'modules')
        (self.source / 'modules/owned.txt').write_text('upstream')
        self.assertEqual(self.deploy.update(), 1)
        self.assertFalse((self.live / 'modules').exists())

    def test_preview_does_not_write_files_or_records(self):
        (self.source / 'config.txt').write_text('new')
        before = installer.fingerprint(self.root)
        self.deploy.preview_update(self.deploy.plan_update())
        self.assertEqual(installer.fingerprint(self.root), before)

    def test_changes_after_preview_abort_before_any_config_is_replaced(self):
        (self.source / 'config.txt').write_text('new')
        plans = self.deploy.plan_update()
        (self.live / 'config.txt').write_text('edit during confirmation')
        with self.assertRaisesRegex(ValueError, 'changed since preview'):
            self.deploy.update(plans)
        self.assertEqual((self.live / 'config.txt').read_text(), 'edit during confirmation')
        self.assertFalse((self.deploy.directory / 'updates').exists())

    def test_repeated_update_is_a_noop(self):
        (self.source / 'config.txt').write_text('new')
        self.deploy.update()
        before = installer.fingerprint(self.root)
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual(installer.fingerprint(self.root), before)

    def test_legacy_clean_record_migrates_to_per_file_tracking(self):
        self.legacy_record()
        (self.source / 'config.txt').write_text('new')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'config.txt').read_text(), 'new')
        self.assertIn('config.txt', self.entry()['files'])

    def test_legacy_exact_source_can_identify_local_edits(self):
        self.legacy_record()
        (self.live / 'config.txt').write_text('local edit')
        self.assertEqual(self.deploy.update(), 0)
        self.assertEqual((self.live / 'config.txt').read_text(), 'local edit')
        self.assertTrue(self.entry()['local_changes'])

    def test_legacy_unknown_baseline_keeps_directory_and_stages_incoming(self):
        self.legacy_record()
        (self.live / 'config.txt').write_text('local edit')
        (self.source / 'config.txt').write_text('upstream')
        self.assertEqual(self.deploy.update(), 1)
        self.assertEqual((self.live / 'config.txt').read_text(), 'local edit')
        self.assertNotIn('files', self.entry())
        reviews = list((self.deploy.directory / 'updates').glob('*/incoming/hypr/config.txt'))
        self.assertEqual([p.read_text() for p in reviews], ['upstream'])

    def test_compiled_shader_uses_installed_baseline_and_rebuilds_on_source_change(self):
        shell = self.repo / 'config/quickshell'
        shader = shell / 'lock/shaders/mainframe-crt.frag'
        shader.parent.mkdir(parents=True)
        shader.write_text('fragment one')
        shader.with_suffix('.frag.qsb').write_text('repository binary')
        def bake(staged):
            src = staged / 'lock/shaders/mainframe-crt.frag'
            src.with_suffix('.frag.qsb').write_text('compiled ' + src.read_text())
        with patch.object(installer, 'bake_lock_shader', side_effect=bake):
            self.deploy.update()
            before = installer.fingerprint(self.config / 'quickshell')
            self.assertEqual(self.deploy.update(), 0)
            self.assertEqual(installer.fingerprint(self.config / 'quickshell'), before)
            shader.write_text('fragment two')
            self.assertEqual(self.deploy.update(), 0)
        actual = self.config / 'quickshell/lock/shaders/mainframe-crt.frag.qsb'
        self.assertEqual(actual.read_text(), 'compiled fragment two')

    def test_interrupted_update_keeps_live_tree_and_original_restore_available(self):
        (self.source / 'config.txt').write_text('new')
        with patch.object(installer, 'publish_config', side_effect=OSError('exchange failed')):
            with self.assertRaises(OSError):
                self.deploy.update()
        self.assertEqual((self.live / 'config.txt').read_text(), 'version one')
        self.assertTrue(self.entry()['pending'])
        with self.assertRaisesRegex(ValueError, 'Interrupted deployment'):
            self.deploy.plan_update()
        self.deploy.restore()
        self.assertTrue((self.live / 'original.txt').exists())

    def test_unmanaged_installation_requires_explicit_initial_install(self):
        self.deploy.record.unlink()
        with self.assertRaisesRegex(ValueError, 'Run install first'):
            self.deploy.plan_update()

    def test_selected_groups_survive_update(self):
        self.assertEqual(self.deploy.load()['groups'], ['animated', 'core'])
        self.deploy.update(groups=['core', 'animated', 'capture', 'wallpapers'])
        self.assertEqual(self.deploy.load()['groups'], ['animated', 'capture', 'core'])


class UpdateCLITests(unittest.TestCase):
    def test_update_flag_and_menu(self):
        self.assertEqual(installer.parser().parse_args(['update', '--dry-run']).command, 'update')
        with patch('builtins.input', return_value='6'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.menu(), 'update')

    def test_update_dry_run_ignores_saved_optional_groups_and_never_mutates(self):
        with patch.object(sys, 'argv', ['install.sh', 'update', '--dry-run']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer.Deployment, 'plan_update', return_value=[]), \
                patch.object(installer.Deployment, 'load', return_value={'groups': ['core', 'animated', 'music', 'editor']}), \
                patch.object(installer, 'resolve_dependencies', return_value=[]) as resolve, \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer, 'install_packages') as packages, \
                patch.object(installer.Deployment, 'update') as update, \
                patch.object(installer.Deployment, 'download_wallpapers') as download, \
                patch('builtins.input', side_effect=AssertionError('preview prompted')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 0)
        self.assertEqual(resolve.call_args.args[1], ['core'])
        packages.assert_not_called()
        update.assert_not_called()
        download.assert_not_called()

    def test_noninteractive_update_keeps_conflicts_visible_and_does_not_download(self):
        with patch.object(sys, 'argv', ['install.sh', 'update', '--yes']), \
                patch.object(installer, 'platform_check'), \
                patch.object(installer.Deployment, 'plan_update', return_value=[]), \
                patch.object(installer.Deployment, 'load', return_value={'groups': ['core']}), \
                patch.object(installer, 'resolve_dependencies', return_value=[]), \
                patch.object(installer, 'compatibility', return_value=[]), \
                patch.object(installer, 'source_compatibility', return_value=[]), \
                patch.object(installer.os, 'geteuid', return_value=1000), \
                patch.object(installer.shutil, 'which', return_value='/usr/bin/tool'), \
                patch.object(installer, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')), \
                patch.object(installer, 'install_packages'), \
                patch.object(installer.Deployment, 'update', return_value=1) as update, \
                patch.object(installer.Deployment, 'install') as install, \
                patch.object(installer.Deployment, 'download_wallpapers') as download, \
                patch('builtins.input', side_effect=AssertionError('noninteractive update prompted')), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(), 2)
        update.assert_called_once_with([], groups=['core'])
        install.assert_not_called()
        download.assert_not_called()


if __name__ == '__main__':
    unittest.main()
