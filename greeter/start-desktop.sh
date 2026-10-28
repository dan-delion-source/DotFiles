#!/bin/sh
# Keep the real watchdog and its diagnostics, without painting the login VT.
exec /usr/bin/systemd-cat --identifier=yozora-hyprland /usr/bin/start-hyprland "$@"
