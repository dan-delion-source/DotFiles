#!/bin/sh
set -eu
if ! command -v python3 >/dev/null 2>&1; then
    # Read-only/recovery commands must never install a bootstrap dependency.
    for arg in "$@"; do
        case "$arg" in
            check|restore|uninstall|greeter-check|greeter-uninstall|--dry-run|--help|-h)
                echo 'Python is required: sudo pacman -Syu --needed python' >&2
                exit 1
                ;;
        esac
    done
    if [ "$(id -u)" = 0 ]; then
        echo 'Run as your desktop user, without sudo.' >&2
        exit 1
    fi
    if ! command -v pacman >/dev/null 2>&1 || ! command -v sudo >/dev/null 2>&1; then
        echo 'Python bootstrap requires an Arch/CachyOS system and a user with sudo access.' >&2
        exit 1
    fi
    echo 'Python is needed to review and install this setup.'
    echo 'Bootstrap command: sudo pacman -Syu --needed python (review the system upgrade).'
    accepted=no
    for arg in "$@"; do
        [ "$arg" != --yes ] || accepted=yes
    done
    if [ "$accepted" != yes ]; then
        printf 'Install Python and continue? [y/N] '
        read -r answer || exit 1
        case "$answer" in y|Y) ;; *) echo 'Cancelled.'; exit 0 ;; esac
    fi
    sudo pacman -Syu --needed python
fi
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B "$base/install/installer.py" "$@"
