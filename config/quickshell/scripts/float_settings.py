#!/usr/bin/env python3
"""Float this shell's Settings window when the Hyprland rule is not loaded."""

import argparse
import json
import re
import subprocess
import time


def settings_window(pid=None):
    result = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True,
                            text=True, timeout=2, check=True)
    for window in json.loads(result.stdout):
        if (window.get("class") == "org.danshell"
                and window.get("title") == "Settings"
                and window.get("mapped")
                and (pid is None or window.get("pid") == pid)):
            return window
    return None


def main(pid=None):
    # The toplevel can become visible in QML before Hyprland maps it.
    for _ in range(20):
        window = settings_window(pid)
        if window is not None:
            break
        time.sleep(0.05)
    else:
        return

    if window.get("floating"):
        return
    address = window.get("address", "")
    if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
        return
    target = f"address:{address}"
    script = (
        f'hl.dispatch(hl.dsp.window.float({{action="set",window="{target}"}}));'
        f'hl.dispatch(hl.dsp.window.resize({{x=900,y=620,exact=true,window="{target}"}}));'
        f'hl.dispatch(hl.dsp.window.center({{window="{target}"}}))'
    )
    subprocess.run(["hyprctl", "eval", script], capture_output=True,
                   timeout=2, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int)
    main(parser.parse_args().pid)
