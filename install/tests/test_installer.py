import contextlib
import errno
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("installer", Path(__file__).parents[1] / "installer.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rice test ")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / "source with spaces"
        for name in ("hypr", "quickshell", "kitty", "fastfetch", "matugen"):
            directory = self.repo / "config" / name
            directory.mkdir(parents=True)
            (directory / "config.txt").write_text(f"new {name}")
        (self.repo / "Wallpapers").mkdir()
        (self.repo / "Wallpapers/wall.jpg").write_bytes(b"fixture")
        self.config, self.data, self.state = [root / p for p in ("config", "data", "state")]
        self.deployment = installer.Deployment(self.repo, self.config, self.data, self.state)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_existing_configs_repeat_install_and_restore(self):
        (self.config / "hypr").mkdir(parents=True)
        (self.config / "hypr/hyprland.conf").write_text("original")
        self.deployment.install()
        first = self.deployment.record.read_bytes()
        self.deployment.install()
        self.assertEqual(first, self.deployment.record.read_bytes())
        self.assertFalse((self.config / "hypr/hyprland.conf").exists())
        self.deployment.restore()
        self.assertEqual((self.config / "hypr/hyprland.conf").read_text(), "original")
        self.assertFalse((self.config / "kitty").exists())
        self.assertFalse((self.data / "wallpapers").exists())

    def test_changed_configs_reject_reinstall_and_preserve_on_restore(self):
        self.deployment.install()
        (self.config / "kitty/config.txt").write_text("personal edits")
        with self.assertRaisesRegex(ValueError, "Changed since installation"):
            self.deployment.install()
        self.deployment.restore()
        preserved = list((self.state / "danshell-installer/preserved").rglob("config.txt"))
        self.assertEqual([p.read_text() for p in preserved], ["personal edits"])

    def test_source_upgrade_keeps_original_backup(self):
        (self.config / "hypr").mkdir(parents=True)
        (self.config / "hypr/original").write_text("original")
        self.deployment.install()
        (self.repo / "config/hypr/config.txt").write_text("upgrade")
        self.deployment.install()
        self.assertEqual((self.config / "hypr/config.txt").read_text(), "upgrade")
        self.deployment.restore()
        self.assertEqual((self.config / "hypr/original").read_text(), "original")

    def test_target_shader_rebuild_keeps_reinstall_repeatable(self):
        def bake(staged):
            (staged / "native-shader.qsb").write_text("target Qt package")
        with patch.object(installer, "bake_lock_shader", side_effect=bake) as compiler:
            self.deployment.install()
            self.deployment.install()
        compiler.assert_called_once()
        entry = next(e for e in self.deployment.load()["entries"]
                     if e["destination"] == str(self.config / "quickshell"))
        self.assertNotEqual(entry["source"], entry["installed"])
        self.assertEqual(entry["installed"], installer.fingerprint(self.config / "quickshell"))
        self.deployment.restore()
        self.assertFalse((self.config / "quickshell").exists())

    def test_shader_build_failure_leaves_existing_target_untouched(self):
        # Arrange the shell first to isolate this pre-replacement failure.
        self.deployment.targets.sort(key=lambda item: item[0].name != "quickshell")
        (self.config / "quickshell").mkdir(parents=True)
        (self.config / "quickshell/original").write_text("original")
        with patch.object(installer, "bake_lock_shader", side_effect=OSError("compiler failed")):
            with self.assertRaises(OSError):
                self.deployment.install()
        self.assertEqual((self.config / "quickshell/original").read_text(), "original")
        self.assertFalse(self.deployment.record.exists())

    def test_existing_symlink_restored_without_changing_target(self):
        other = Path(self.temp.name) / "other"
        other.mkdir()
        (other / "untouched").write_text("old")
        self.config.mkdir()
        (self.config / "kitty").symlink_to(other, target_is_directory=True)
        self.deployment.install()
        self.assertEqual((other / "untouched").read_text(), "old")
        self.deployment.restore()
        self.assertEqual((self.config / "kitty").readlink(), other)

    def test_overlapping_checkout_and_state_rejected(self):
        with self.assertRaisesRegex(ValueError, "overlaps checkout"):
            installer.Deployment(self.repo, self.repo / "config", self.data, self.state)
        with self.assertRaisesRegex(ValueError, "Installer state"):
            installer.Deployment(self.repo, self.config, self.data, self.config / "kitty")

    def test_restore_dry_run_writes_nothing(self):
        self.deployment.install()
        before = installer.fingerprint(Path(self.temp.name))
        self.deployment.restore(dry_run=True)
        self.assertEqual(installer.fingerprint(Path(self.temp.name)), before)

    def test_failed_replacement_is_recoverable(self):
        (self.config / "hypr").mkdir(parents=True)
        (self.config / "hypr/original").write_text("original")
        with patch.object(installer, "publish_config", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                self.deployment.install()
        self.assertEqual((self.config / "hypr/original").read_text(), "original")
        self.deployment.restore()
        self.assertEqual((self.config / "hypr/original").read_text(), "original")

    def test_missing_backup_never_removes_destination(self):
        (self.config / "hypr").mkdir(parents=True)
        (self.config / "hypr/original").write_text("original")
        self.deployment.install()
        entry = self.deployment.load()["entries"][0]
        installer.remove(Path(entry["backup"]))
        with self.assertRaisesRegex(ValueError, "Backup missing"):
            self.deployment.restore()
        self.assertTrue((self.config / "hypr/config.txt").exists())


class AtomicPublishTests(unittest.TestCase):
    def test_watched_entry_never_disappears_during_repeated_directory_swaps(self):
        with tempfile.TemporaryDirectory(prefix="hypr config swap ") as temporary:
            root = Path(temporary)
            staged, live = root / "staged", root / "hypr"
            for path, text in ((staged, "new config"), (live, "old config")):
                path.mkdir()
                (path / "hyprland.lua").write_text(text)
                (path / "modules").mkdir()
            stopped, started = threading.Event(), threading.Event()
            errors, observed = [], []

            def read_entry():
                started.set()
                while not stopped.is_set():
                    try:
                        value = (live / "hyprland.lua").read_text()
                        if value not in ("old config", "new config"):
                            errors.append(value)
                        observed.append(value)
                    except OSError as error:
                        errors.append(str(error))

            reader = threading.Thread(target=read_entry)
            reader.start()
            self.assertTrue(started.wait(timeout=2))
            try:
                for _ in range(300):
                    installer.publish_config(staged, live)
            finally:
                stopped.set()
                reader.join(timeout=2)
            self.assertFalse(reader.is_alive())
            self.assertTrue(observed)
            self.assertEqual(errors, [])
            self.assertEqual((live / "hyprland.lua").read_text(), "old config")
            self.assertEqual((staged / "hyprland.lua").read_text(), "new config")

    def test_failed_atomic_exchange_keeps_both_trees_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staged, live = root / "staged", root / "hypr"
            for path, text in ((staged, "new"), (live, "old")):
                path.mkdir()
                (path / "hyprland.lua").write_text(text)
            before = installer.fingerprint(root)
            libc = Mock()
            libc.renameat2.return_value = -1
            with patch.object(installer.ctypes, "CDLL", return_value=libc), \
                    patch.object(installer.ctypes, "get_errno", return_value=errno.EOPNOTSUPP):
                with self.assertRaisesRegex(OSError, "existing config kept"):
                    installer.publish_config(staged, live)
            self.assertEqual(installer.fingerprint(root), before)


class DependencyTests(unittest.TestCase):
    def test_repository_provider_preferred_over_aur(self):
        manifest = {"features": {"core": {"dependencies": [
            {"packages": ["tool", "tool-bin"], "commands": ["tool"]}]}}}
        def query(args):
            return subprocess.CompletedProcess(args, 0 if args[1:] == ["-Si", "tool-bin"] else 1)
        with patch.object(installer, "run", side_effect=query):
            rows = installer.resolve_dependencies(manifest, ["core"])
        self.assertEqual((rows[0]["source"], rows[0]["package"]), ("repository", "tool-bin"))

    def test_installed_alternative_wins_without_repository_queries(self):
        manifest = {"features": {"core": {"dependencies": [
            {"packages": ["tool", "tool-bin"], "commands": ["tool"]}]}}}
        def query(args):
            self.assertEqual(args[1], "-Q")
            return subprocess.CompletedProcess(args, 0 if args[-1] == "tool-bin" else 1)
        with patch.object(installer, "run", side_effect=query):
            row = installer.resolve_dependencies(manifest, ["core"])[0]
        self.assertEqual((row["source"], row["package"]), ("installed", "tool-bin"))

    def test_aur_candidates_are_verified_and_selected(self):
        dependencies = [{"source": "AUR", "packages": ["tool", "tool-bin"], "package": "tool"}]
        response = io.BytesIO(json.dumps({"results": [{"Name": "tool-bin"}]}).encode())
        with patch.object(installer.urllib.request, "urlopen", return_value=contextlib.closing(response)):
            installer.verify_aur(dependencies)
        self.assertEqual(dependencies[0]["package"], "tool-bin")

    def test_unknown_aur_candidate_is_rejected(self):
        response = io.BytesIO(b'{"results": []}')
        with patch.object(installer.urllib.request, "urlopen", return_value=contextlib.closing(response)):
            with self.assertRaisesRegex(ValueError, "Not found"):
                installer.verify_aur([{"source": "AUR", "packages": ["typo"]}])

    def test_unknown_group_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown groups"):
            installer.selection({"features": {"core": {}}}, ["typo"])

    def test_version_validation(self):
        self.assertTrue(installer.version_at_least("Hyprland 0.56.2", (0, 56, 2)))
        self.assertFalse(installer.version_at_least("Hyprland 0.54.0", (0, 56, 2)))
        self.assertFalse(installer.version_at_least("unknown", (0, 56, 2)))


if __name__ == "__main__":
    unittest.main()
