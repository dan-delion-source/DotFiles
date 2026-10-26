import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "greeting_under_test", Path(__file__).resolve().parents[1] / "scripts/greeting.py")
greeting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(greeting)


class GreetingTests(unittest.TestCase):
    def test_list_cli_exits_successfully_with_json(self):
        result = subprocess.run([sys.executable, greeting.__file__, "list"],
                                capture_output=True, text=True, check=True)
        self.assertIsInstance(json.loads(result.stdout), list)
        self.assertEqual(result.stderr, "")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.config = base / "config.jsonc"
        self.config.write_text('// preserve comments and custom modules\n'
                               '{"logo":{"type":"kitty-icat","source":"old.gif","width":30},'
                               '"modules":[{"type":"custom","format":"keep me"}]}')
        self.logos = base / "logos"
        self.logos.mkdir()
        (self.logos / "arch.txt").write_text("/\\\n")
        (self.logos / "cat.gif").write_bytes(b"GIF89a")
        self.state = base / "state"
        self.state.mkdir()
        for scene in greeting.SCENES:
            (self.state / f"greeting-{scene}.gif").write_bytes(b"GIF89a")
        values = dict(STATE_DIR=str(self.state), FASTFETCH_CONFIG=str(self.config),
                      LOGO_DIR=str(self.logos), CHOICE_FILE=str(self.state / "greeting"),
                      LINK=str(self.state / "greeting.gif"),
                      PAINT_FILE=str(self.state / "paint.json"))
        self.overrides = patch.multiple(greeting, **values)
        self.overrides.start()
        self.addCleanup(self.overrides.stop)

    def test_every_choice_uses_existing_source_and_keeps_custom_modules(self):
        for choice in greeting.CHOICES:
            with self.subTest(choice=choice):
                self.assertTrue(greeting.choose(choice))
                config = self.config.read_text()
                self.assertIn('// preserve comments and custom modules', config)
                self.assertIn('"format":"keep me"', config)
                self.assertEqual(greeting.read_choice(), choice)
                expected = "file" if choice == "arch" else "kitty-icat"
                self.assertIn(f'"type":"{expected}"', config)
                if choice not in greeting.EXTRA_LOGOS:
                    self.assertTrue(Path(greeting.LINK).is_file())

    def test_one_off_scene_overrides_arch_renderer_without_changing_saved_choice(self):
        self.assertTrue(greeting.choose("arch"))
        before = self.config.read_bytes()
        with patch.object(greeting.subprocess, "call", return_value=0) as runner:
            self.assertEqual(greeting.show(["koi", "--structure", "title"]), 0)
        args = runner.call_args.args[0]
        self.assertEqual(args[args.index("--logo-type") + 1], "kitty-icat")
        self.assertEqual(args[args.index("--logo") + 1], str(self.state / "greeting-koi.gif"))
        self.assertEqual(args[-2:], ["--structure", "title"])
        self.assertEqual(greeting.read_choice(), "arch")
        self.assertEqual(self.config.read_bytes(), before)

    def test_missing_scenes_are_generated_before_selection_and_render_failure_preserves_config(self):
        (self.state / "greeting-koi.gif").unlink()
        before = self.config.read_bytes()
        with patch.object(greeting, "draw", return_value=False) as draw, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(greeting.choose("koi"))
            draw.assert_called_once()
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(Path(greeting.CHOICE_FILE).exists())

    def test_unknown_choice_does_not_run_fastfetch_or_change_selection(self):
        before = self.config.read_bytes()
        with patch.object(greeting.subprocess, "call") as runner, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(greeting.show(["unknown"]), 1)
            runner.assert_not_called()
        self.assertEqual(self.config.read_bytes(), before)

    def test_discovery_updates_files_and_preserves_builtin_ids(self):
        custom = self.logos / "new_logo.PNG"
        custom.write_bytes(b"image")
        (self.logos / ".hidden.gif").write_bytes(b"GIF89a")
        (self.logos / "ignore.svg").write_text("svg")
        (self.logos / "folder.gif").mkdir()
        entries = {entry["id"]: entry for entry in greeting.list_greetings()}
        self.assertEqual(set(entries), set(greeting.CHOICES) | {"logo:new_logo.PNG"})
        self.assertEqual(entries["arch"]["kind"], "text")
        self.assertEqual(entries["logo:new_logo.PNG"]["label"], "New Logo")
        self.assertEqual(entries["logo:new_logo.PNG"]["path"], str(custom))
        old_version = entries["logo:new_logo.PNG"]["version"]
        custom.write_bytes(b"replacement image")
        refreshed = {entry["id"]: entry for entry in greeting.list_greetings()}
        self.assertNotEqual(old_version, refreshed["logo:new_logo.PNG"]["version"])
        custom.unlink()
        self.assertNotIn("logo:new_logo.PNG", {entry["id"] for entry in greeting.list_greetings()})

    def test_custom_files_choose_render_and_keep_saved_missing_choice(self):
        for filename, renderer in [('my "logo".png', 'kitty-icat'), ('my ascii.txt', 'file'),
                                   ('moving.gif', 'kitty-icat'), ('photo.jpeg', 'kitty-icat'),
                                   ('image.webp', 'kitty-icat')]:
            with self.subTest(filename=filename):
                source = self.logos / filename
                source.write_bytes(b"test")
                choice = greeting.file_choice(filename)
                self.assertTrue(greeting.choose(choice))
                config = json.loads(self.config.read_text().split('\n', 1)[1])
                self.assertEqual(config["logo"]["source"], str(source))
                self.assertEqual(config["logo"]["type"], renderer)
                with patch.object(greeting.subprocess, "call", return_value=0) as runner:
                    self.assertEqual(greeting.show([]), 0)
                self.assertEqual(runner.call_args.args[0][-1], str(source))
                before = self.config.read_bytes()
                source.unlink()
                self.assertEqual(greeting.read_choice(), choice)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertFalse(greeting.choose(choice))
                self.assertEqual(self.config.read_bytes(), before)
        self.assertTrue(greeting.choose("arch"))

    def test_file_ids_cannot_escape_logo_directory(self):
        for choice in ("logo:../outside.png", "logo:/tmp/outside.png", "logo:.hidden.gif",
                       "logo:ignore.svg", "logo:"):
            with self.subTest(choice=choice), contextlib.redirect_stderr(io.StringIO()):
                self.assertFalse(greeting.choose(choice))

    def test_missing_folder_keeps_generated_scenes(self):
        with patch.object(greeting, "LOGO_DIR", str(self.logos / "missing")):
            self.assertEqual({entry["id"] for entry in greeting.list_greetings()},
                             set(greeting.SCENES) | {"random"})


if __name__ == "__main__":
    unittest.main()
