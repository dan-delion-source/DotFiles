#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
runtime=$(mktemp -d /tmp/yozora-greeter-XXXXXX)
chmod 700 "$runtime"
trap 'rm -rf -- "$runtime"' EXIT
trap 'exit 143' HUP INT TERM
export XDG_RUNTIME_DIR="$runtime"
unset WAYLAND_DISPLAY HYPRLAND_INSTANCE_SIGNATURE
export XDG_CURRENT_DESKTOP=Hyprland
export QT_QPA_PLATFORM=wayland
export QT_QUICK_CONTROLS_STYLE=Basic
export QT_QPA_PLATFORMTHEME=
# The user directory is private; the greeter runs only immutable installed code.
dbus-run-session -- /usr/bin/start-hyprland -- --config "$base/hyprland.lua" >"$runtime/compositor.log" 2>&1 || :
if [ -f "$runtime/yozora-handoff" ]; then
    exit 0
fi
logger -t yozora-greeter 'Graphical login failed; using text login. Inspect greetd journal and greeter-check.'
cat "$runtime/compositor.log" >&2
rm -rf -- "$runtime"
trap - EXIT HUP INT TERM
exec /usr/bin/agreety --cmd "$base/start-desktop.sh"
