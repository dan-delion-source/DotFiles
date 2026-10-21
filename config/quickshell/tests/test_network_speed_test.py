"""The manual internet test protocol and transfer bounds, without network IO."""

import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/network_speed_test.py"
spec = importlib.util.spec_from_file_location("network_speed_test", SCRIPT)
speed_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speed_test)


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.request = None

    def open(self, request, timeout):
        self.request = request
        if timeout != speed_test.REQUEST_TIMEOUT:
            raise AssertionError("request timeout changed")
        return io.BytesIO(self.response)


class ManualSpeedTestTests(unittest.TestCase):
    def test_transfer_budget(self):
        self.assertEqual(speed_test.DOWNLOAD_BYTES * speed_test.PARALLEL_REQUESTS, 32_000_000)
        self.assertEqual(speed_test.UPLOAD_BYTES * speed_test.PARALLEL_REQUESTS, 16_000_000)

    def test_download_requires_complete_sample(self):
        opener = FakeOpener(b"abcd")
        with patch.object(speed_test, "make_opener", return_value=opener):
            self.assertEqual(speed_test.download_once(4), 4)
            self.assertIn("/__down?bytes=4", opener.request.full_url)
        with patch.object(speed_test, "make_opener", return_value=FakeOpener(b"abc")):
            with self.assertRaisesRegex(ValueError, "before the test sample"):
                speed_test.download_once(4)

    def test_upload_uses_post_and_counts_sent_bytes(self):
        opener = FakeOpener(b"ok")
        with patch.object(speed_test, "make_opener", return_value=opener):
            self.assertEqual(speed_test.upload_once(b"abcd"), 4)
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertEqual(opener.request.data, b"abcd")

    def test_run_emits_phases_and_result_only_when_called(self):
        events = []
        with patch.object(speed_test, "measure", side_effect=[12.3, 4.5]), \
                patch.object(speed_test, "emit", side_effect=lambda event, **fields: events.append((event, fields))):
            speed_test.run()
        self.assertEqual(events, [
            ("phase", {"name": "download"}),
            ("partial", {"name": "download", "mbps": 12.3}),
            ("phase", {"name": "upload"}),
            ("result", {"download_mbps": 12.3, "upload_mbps": 4.5}),
        ])


if __name__ == "__main__":
    unittest.main()
