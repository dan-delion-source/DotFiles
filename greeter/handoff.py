#!/usr/bin/env python3
"""Acknowledge handoff before stopping only this greeter compositor."""
import os
from pathlib import Path
import subprocess
Path(os.environ['XDG_RUNTIME_DIR'], 'yozora-handoff').touch(mode=0o600)
subprocess.run(['hyprctl', 'eval', 'hl.dispatch(hl.dsp.exit())'], capture_output=True, timeout=3)
