# Install and restore one config at a time

Run these commands from the repository root. Python 3 is the only installer dependency.

```sh
python3 install/configs.py list
python3 install/configs.py status noctalia
python3 install/configs.py install noctalia
python3 install/configs.py uninstall noctalia
```

Replace `noctalia` with `hypr`, `matugen`, `kitty`, `alacritty`, or `fastfetch` to manage that config. Install Matugen as well if you want the wallpaper-generated colors used by the Noctalia, Hyprland, Kitty, and Alacritty configs. The installer links the files from this repository into `~/.config/<name>/`; keep this repository at its current path while a group is installed. It does not install application packages, start services, or overwrite unrelated files in those folders.

## Step by step: Noctalia

1. Check what is installed: `python3 install/configs.py status noctalia`.
2. Install its config: `python3 install/configs.py install noctalia`.
3. Check the link: `ls -l ~/.config/noctalia/config.toml`.
4. When you want the old config back, run `python3 install/configs.py uninstall noctalia`.

Before replacing a file, the installer saves the original at `~/.local/state/dotfiles-installer/<name>/backups/`. An original symlink is saved as a symlink. On uninstall, it removes only links it created and restores those originals. If a managed file was changed or a backup is missing, uninstall stops without removing files; inspect that path and restore the expected link before retrying. Generated palettes and other files are left alone.

`XDG_CONFIG_HOME` and `XDG_STATE_HOME` are respected if set. The state directory also contains `manifest.json`; keep it with the backups until uninstall completes.
