import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("monitors", Path(__file__).parents[1] / "scripts/monitors.py")
monitors = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitors)


class MonitorTests(unittest.TestCase):
    def test_detection_accepts_unfamiliar_connectors_and_disabled_outputs(self):
        payload = [
            {"id": 1, "name": "DP-7", "description": "Display A serial123",
             "width": 3840, "height": 2160, "scale": 1.5,
             "availableModes": ["3840x2160@60.00Hz", "1920x1080@144.00Hz"]},
            {"id": 2, "name": "USB-C-9", "description": "Display B serial456", "disabled": True},
        ]
        with patch.object(monitors, "hyprctl", return_value=subprocess.CompletedProcess([], 0, json.dumps(payload))):
            detected = monitors.read()
        self.assertEqual([m["name"] for m in detected], ["DP-7", "USB-C-9"])
        self.assertEqual(detected[0]["scale"], 1.5)
        self.assertTrue(detected[1]["disabled"])
        self.assertEqual(detected[1]["mode"], "preferred")

    def test_saved_display_rules_use_identity_and_apply_together(self):
        rules = [
            {"output": "desc:Display A serial123", "mode": "preferred", "position": "auto", "scale": "auto"},
            {"output": "desc:Display B serial456", "disabled": True},
        ]
        with patch.object(monitors, "hyprctl", return_value=subprocess.CompletedProcess([], 0, "ok")) as call:
            self.assertEqual(monitors.apply(rules), 0)
        command = call.call_args.args
        self.assertEqual(command[0], "eval")
        self.assertIn('output = "desc:Display A serial123"', command[1])
        self.assertIn('scale = "auto"', command[1])
        self.assertEqual(command[1].count("hl.monitor"), 2)

    def test_invalid_settings_never_reach_compositor(self):
        with patch.object(monitors, "hyprctl") as call:
            self.assertEqual(monitors.apply([{"output": "DP-7", "scale": -2}]), 1)
        call.assert_not_called()

    def test_no_running_compositor_returns_empty_detection(self):
        with patch.object(monitors, "hyprctl", return_value=None):
            self.assertEqual(monitors.read(), [])


if __name__ == "__main__":
    unittest.main()
