# DotFiles

## Wallpaper theming

Matugen is configured to generate colors from a wallpaper into:

- Noctalia: `~/.config/noctalia/palettes/Matugen.json`
- Hyprland: `~/.config/hypr/colors.lua`
- Kitty: `~/.config/kitty/themes/matugen.conf`
- Alacritty: `~/.config/alacritty/themes/matugen.toml`
- GTK 3/4: `~/.config/gtk-3.0/gtk.css` and `~/.config/gtk-4.0/gtk.css`

After linking this repo into `~/.config`, apply a wallpaper and regenerate the theme with:

```sh
scripts/wallpaper-theme.sh /path/to/wallpaper
```

The script sets the wallpaper through Noctalia when available, runs Matugen, switches Noctalia to the generated `Matugen` custom palette, reapplies templates, and reloads Hyprland.
