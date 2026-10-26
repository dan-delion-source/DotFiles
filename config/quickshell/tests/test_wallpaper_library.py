import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import theme_manager


class WallpaperLibraryTests(unittest.TestCase):
    def test_lists_stills_and_animated_from_separate_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            animated = root / "animated"
            animated.mkdir()
            for filename in ("new wallpaper.JPG", "other.webp", ".hidden.png", "ignore.txt"):
                (root / filename).write_bytes(b"fixture")
            (root / "folder.png").mkdir()
            (animated / "motion.gif").write_bytes(b"fixture")
            (animated / "video.mp4").write_bytes(b"fixture")
            (animated / "ignore.png").write_bytes(b"fixture")
            with patch.object(theme_manager, "WALLPAPERS_DIR", str(root)), \
                    patch.object(theme_manager, "ANIMATED_DIR", str(animated)), \
                    patch.object(theme_manager, "poster_of", side_effect=lambda path: path + ".png"):
                entries = theme_manager.list_wallpapers()
                self.assertEqual({Path(entry["path"]).name for entry in entries},
                                 {"new wallpaper.JPG", "other.webp"})
                self.assertEqual({Path(entry["path"]).name for entry in theme_manager.list_animated()},
                                 {"motion.gif", "video.mp4"})
                (root / "new wallpaper.JPG").rename(root / "renamed.png")
                (root / "other.webp").unlink()
                self.assertEqual(theme_manager.list_wallpapers(),
                                 [{"name": "Renamed", "path": str(root / "renamed.png")}])

    def test_missing_libraries_are_empty_without_creating_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "absent"
            with patch.object(theme_manager, "WALLPAPERS_DIR", str(root)), \
                    patch.object(theme_manager, "ANIMATED_DIR", str(root / "animated")):
                self.assertEqual(theme_manager.list_wallpapers(), [])
                self.assertEqual(theme_manager.list_animated(), [])
                self.assertFalse(root.exists())

    @unittest.skipUnless(shutil.which("inotifywait"), "inotify-tools unavailable")
    def test_real_watch_handles_files_and_directory_recreation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "Wallpapers"
            process = subprocess.Popen([sys.executable, str(SCRIPTS / "watch_wallpapers.py"), str(root)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            def notification():
                ready, _, _ = select.select([process.stdout], [], [], 4)
                self.assertTrue(ready, "watcher did not report a library change")
                self.assertIn(b"changed", os.read(process.stdout.fileno(), 65536))

            def drain():
                # Allow directory re-arming to finish, then discard preceding events.
                deadline = time.monotonic() + 1.2
                while time.monotonic() < deadline:
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if ready:
                        os.read(process.stdout.fileno(), 65536)

            try:
                notification()
                root.mkdir()
                notification()
                drain()
                image = root / "new wallpaper.png"
                image.write_bytes(b"first")
                notification()
                drain()
                image.write_bytes(b"replacement")
                notification()
                drain()
                image = image.rename(root / "renamed.png")
                notification()
                drain()
                image.unlink()
                notification()
                animated = root / "animated"
                animated.mkdir()
                notification()
                drain()
                (animated / "motion.gif").write_bytes(b"GIF89a")
                notification()
                drain()
                (animated / "motion.gif").unlink()
                animated.rmdir()
                notification()
                drain()
                root.rmdir()
                notification()
                drain()
                root.mkdir()
                notification()
                drain()
                (root / "after recreation.jpg").write_bytes(b"new")
                notification()
            finally:
                process.terminate()
                process.wait(timeout=5)
                process.stdout.close()
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
