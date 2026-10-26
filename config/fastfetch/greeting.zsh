# Source from .zshrc; all logo choices and paths are owned by greeting.py.
function fa() {
    local greeting_script="${XDG_CONFIG_HOME:-$HOME/.config}/quickshell/scripts/greeting.py"
    if [[ -r "$greeting_script" ]]; then
        python3 "$greeting_script" show "$@"
    else
        command fastfetch "$@"
    fi
}
