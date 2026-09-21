#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  printf 'usage: %s /path/to/wallpaper\n' "${0##*/}" >&2
  exit 2
fi

wallpaper=$1

if [[ ! -f "$wallpaper" ]]; then
  printf 'wallpaper not found: %s\n' "$wallpaper" >&2
  exit 1
fi

mkdir -p \
  "$HOME/.config/matugen/templates" \
  "$HOME/.config/noctalia/palettes" \
  "$HOME/.config/hypr" \
  "$HOME/.config/kitty/themes" \
  "$HOME/.config/alacritty/themes" \
  "$HOME/.config/gtk-3.0" \
  "$HOME/.config/gtk-4.0"

if command -v noctalia >/dev/null 2>&1; then
  noctalia msg wallpaper-set "$wallpaper" >/dev/null 2>&1 || true
elif command -v swww >/dev/null 2>&1; then
  swww img "$wallpaper" >/dev/null 2>&1 || true
fi

matugen image "$wallpaper" \
  --config "$HOME/.config/matugen/config.toml" \
  --mode dark \
  --type scheme-tonal-spot \
  --source-color-index 0

if command -v noctalia >/dev/null 2>&1; then
  noctalia msg color-scheme-set custom Matugen >/dev/null 2>&1 || true
  noctalia msg templates-apply >/dev/null 2>&1 || true
  noctalia msg config-reload >/dev/null 2>&1 || true
fi

if command -v hyprctl >/dev/null 2>&1; then
  hyprctl reload >/dev/null 2>&1 || true
fi

printf 'theme generated from %s\n' "$wallpaper"
