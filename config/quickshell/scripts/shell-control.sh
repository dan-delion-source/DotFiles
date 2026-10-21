#!/bin/sh
# Operate only on the config next to this script, including through symlinks.
set -eu
script=$(readlink -f -- "$0")
config=$(dirname -- "$(dirname -- "$script")")
case "${1:-start}" in
    start) exec qs --path "$config" --no-duplicate --daemonize ;;
    restart)
        # IPC reload preserves the instance and does not kill another config.
        if qs ipc --path "$config" call shell reload; then exit 0; fi
        exec qs --path "$config" --no-duplicate --daemonize
        ;;
    stop) exec qs kill --path "$config" ;;
    *) printf '%s\n' 'Usage: shell-control.sh [start|restart|stop]' >&2; exit 2 ;;
esac
