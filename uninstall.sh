#!/bin/sh
# Restore installer-managed configs; keep packages and personal shell state.
set -eu
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Python is required for config recovery: sudo pacman -S python' >&2
    exit 1
fi
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B "$base/install/installer.py" uninstall "$@"
