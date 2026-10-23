import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

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
        replace = Path.replace
        def fail_stage(path, target):
            if path.name == "config" and path.parent.name.startswith(".danshell-"):
                raise OSError("simulated disk failure")
            return replace(path, target)
        with patch.object(Path, "replace", fail_stage):
            with self.assertRaises(OSError):
                self.deployment.install()
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
