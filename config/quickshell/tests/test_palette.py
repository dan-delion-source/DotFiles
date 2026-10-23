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

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import palette
import theme_manager


class PaletteTests(unittest.TestCase):
    def fixture(self):
        return {"colors": {role: {"dark": {"color": "#123456"}}
                           for role in palette.ROLES.values()}}

    def test_matugen_roles_map_to_existing_shell_api(self):
        result = palette.from_json(self.fixture())
        self.assertEqual(set(result), set(palette.ROLES))
        self.assertEqual(result["accent"], "#123456")

    def test_incomplete_or_invalid_palette_rejected(self):
        data = self.fixture()
        data["colors"]["primary"]["dark"]["color"] = "not a colour"
        with self.assertRaises(ValueError):
            palette.from_json(data)

    def test_generation_is_noninteractive_and_runs_no_template_hooks(self):
        result = subprocess.CompletedProcess([], 0, json.dumps(self.fixture()), "")
        with patch.object(palette.subprocess, "run", return_value=result) as runner:
            palette.generate("wallpaper with spaces.jpg")
        command = runner.call_args.args[0]
        self.assertIn("--dry-run", command)
        self.assertIn("--source-color-index", command)
        self.assertEqual(command[2], "wallpaper with spaces.jpg")

    def test_generation_failure_keeps_last_good_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            cached = Path(directory) / "palette.json"
            expected = palette.from_json(self.fixture())
            cached.write_text(json.dumps(expected))
            image = Path(directory) / "wall.jpg"
            image.write_bytes(b"fixture")
            with patch.object(theme_manager, "DYNAMIC_COLORS_FILE", str(cached)), \
                 patch.object(theme_manager, "build_palette", side_effect=FileNotFoundError("matugen")), \
                 contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(theme_manager.extract_colors(str(image)), expected)
            self.assertIn("reselect the wallpaper", errors.getvalue())
            self.assertEqual(json.loads(cached.read_text()), expected)

    def test_first_generation_failure_returns_no_fabricated_palette(self):
        with patch.object(theme_manager, "DYNAMIC_COLORS_FILE", "/nonexistent/palette.json"), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(theme_manager.extract_colors("/nonexistent/image.jpg"))


if __name__ == "__main__":
    unittest.main()
