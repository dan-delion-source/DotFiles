#!/usr/bin/env python3

# ╭──────────────────────────────────────────────────────────────────────────╮
# │                                                                          │
# │   P R I V A C Y                                                          │
# │   which programs have the camera open · on every open and close          │
# │                                                                          │
# │   github.com/andreumassanet/impasto                                      │
# │                                                                          │
# ╰──────────────────────────────────────────────────────────────────────────╯

"""Print, as a JSON line, the programs holding a camera device open.

Usage: privacy.py

Most programs open /dev/video* themselves rather than through PipeWire, so
the device is watched with inotify and the processes holding it are found in
/proc when it is opened or closed; nothing is polled. Only this user's
processes can be read, which leaves out the face unlock, run as root at the
lock screen. PipeWire and WirePlumber are reported as `pipewire`: the program
behind them is a PipeWire stream, which the shell reads itself.
"""

import ctypes
import glob
import json
import os
import signal
import subprocess
import sys

DEVICES = "/dev/video*"
BROKERS = {"pipewire", "wireplumber"}


def holders(devices):
    found = set()
    for fd_dir in glob.glob("/proc/[0-9]*/fd"):
        try:
            links = [os.readlink(os.path.join(fd_dir, fd)) for fd in os.listdir(fd_dir)]
        except OSError:
            continue
        if not any(link in devices for link in links):
            continue
        pid_dir = os.path.dirname(fd_dir)
        try:
            with open(os.path.join(pid_dir, "comm"), encoding="utf-8") as source:
                name = source.read().strip()
        except OSError:
            continue
        found.add("pipewire" if name in BROKERS else name)
    return sorted(found)


def report(devices, last):
    now = holders(devices)
    if now != last:
        print(json.dumps({"camera": now}), flush=True)
    return now


def die_with_parent():
    """Take inotifywait down with this script when the shell stops it."""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG


def main():
    devices = set(glob.glob(DEVICES))
    last = report(devices, None)
    if not devices:
        return
    watch = subprocess.Popen(
        ["inotifywait", "-m", "-q", "-e", "open,close", "--format", "%w", *sorted(devices)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        preexec_fn=die_with_parent)
    if watch.stdout is None:
        return
    for _ in watch.stdout:
        last = report(devices, last)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(0)
