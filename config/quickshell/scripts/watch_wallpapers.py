#!/usr/bin/env python3
"""Notify the shell when its wallpaper library changes, without scanning it.

Watch the stills, animated directory and their nearest existing parent. Re-arm
when directories are created, removed or replaced. The shell debounces these
notifications and queues scans, keeping video poster generation off this loop.
"""

import ctypes
import os
from pathlib import Path
import select
import signal
import subprocess
import sys


def watch_paths(root):
    ancestor = root.parent
    while not ancestor.is_dir() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    paths = [ancestor, root, root / "animated"]
    return {str(path): (path.stat().st_dev, path.stat().st_ino)
            for path in paths if path.is_dir()}


def die_with_parent():
    ctypes.CDLL(None).prctl(1, signal.SIGTERM)


def watch(root):
    root = Path(root).absolute()
    child = None
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        while True:
            paths = watch_paths(root)
            child = subprocess.Popen(
                ["inotifywait", "-m", "-e",
                 "close_write,create,delete,moved_to,moved_from,attrib,delete_self,move_self",
                 "--format", "%w%f", *paths],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=die_with_parent)
            for line in iter(child.stderr.readline, b""):
                if b"Watches established." in line:
                    break
            else:
                child.wait()
                raise RuntimeError(f"Could not establish directory watches (status {child.returncode})")
            # Covers the interval between the initial scan and watcher setup.
            print("changed", flush=True)
            pending = b""
            while child.poll() is None:
                ready, _, _ = select.select([child.stdout], [], [], 1)
                if ready:
                    chunk = os.read(child.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    pending += chunk
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        path = Path(os.fsdecode(line))
                        if path == root or root in path.parents:
                            print("changed", flush=True)
                if watch_paths(root) != paths:
                    break
            if child.poll() is not None and child.returncode:
                raise RuntimeError(f"inotifywait exited with status {child.returncode}")
            child.terminate()
            child.wait()
            child.stdout.close()
            child.stderr.close()
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
            child.wait()
            if child.stdout:
                child.stdout.close()
            if child.stderr:
                child.stderr.close()


if __name__ == "__main__":
    try:
        watch(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Pictures/Wallpapers")
    except (OSError, RuntimeError) as error:
        sys.stderr.write(f"Cannot watch wallpapers: {error}\n")
        sys.exit(1)
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(0)
