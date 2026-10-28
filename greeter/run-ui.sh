#!/bin/sh
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
qs --path "$base"
status=$?
if [ ! -f "$XDG_RUNTIME_DIR/yozora-handoff" ]; then
    printf '%s\n' "$status" > "$XDG_RUNTIME_DIR/yozora-ui-failed"
    hyprctl eval 'hl.dispatch(hl.dsp.exit())' >/dev/null 2>&1 || :
fi
# handoff.py already requested exit after a successful login. Do not send a
# second dispatcher request while the compositor is tearing down its outputs.
