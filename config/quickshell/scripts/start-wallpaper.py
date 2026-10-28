#!/usr/bin/env python3
"""Prepare the saved background before QuickShell loads, without palette work."""
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def ready():
    try:
        return subprocess.run(['awww', 'query'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=0.2).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def prepare():
    display = os.environ.get('WAYLAND_DISPLAY')
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not display or not runtime or not shutil.which('awww'):
        return 0
    # Concurrent starts must not launch competing daemons. This lock belongs
    # only to this user's display, and is released even if startup fails.
    key = hashlib.sha256(display.encode()).hexdigest()[:16]
    with open(Path(runtime) / f'yozora-wallpaper-{key}.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not ready():
            # The shell's saved selection is authoritative, so don't first
            # display an old awww cache image and then replace it.
            subprocess.Popen(['awww-daemon', '--no-cache'], stdout=subprocess.DEVNULL,
                             start_new_session=True)
            deadline = time.monotonic() + 2
            while not ready():
                if time.monotonic() >= deadline:
                    print('Wallpaper daemon not ready; the shell will retry restoration.', file=sys.stderr)
                    return 3
                time.sleep(0.05)
        return subprocess.run([sys.executable, str(Path(__file__).with_name('theme_manager.py')),
                               'restore'], timeout=10).returncode


if __name__ == '__main__':
    try:
        sys.exit(prepare())
    except (OSError, subprocess.SubprocessError) as error:
        print(f'Wallpaper startup failed: {error}', file=sys.stderr)
        sys.exit(1)
