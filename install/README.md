# Installer

See the root [README](../README.md) for prerequisites, optional groups,
installation, restoration, and validation limits.

- `../install.sh`: small numbered terminal menu (run from this directory).
- `../install.sh check`: read-only dependency, compatibility and wallpaper-service audit.
- `../install.sh install --dry-run`: preview without changing files or packages.
- `../install.sh install`: choose optional groups, review the changes and confirm.
- `../install.sh update --dry-run`: preview updates to an existing managed installation.
- `../install.sh update`: apply checkout changes, keeping local edits and saving conflicts for review.
- `../uninstall.sh --dry-run`: preview config uninstallation.
- `../uninstall.sh`: restore original configs and preserve later edits; keep wallpapers.
- `../install.sh restore`: recover originals, preserving later configuration edits.
- `../install.sh wallpapers`: download/retry only the optional external wallpaper collection.

`../packages/pacman.txt` and `../packages/aur.txt` hold package names, grouped by
feature. The AUR list contains only `matugen`, using its main package.
`dependencies.json` maps package IDs to commands, services and features.
`installer.py` resolves
installed and repository providers before using verified AUR candidates. It
validates versions, installed QML modules and QML parsing without starting a shell.
It uses copies rather than links, records content fingerprints, and keeps original
backups across repeated installations. Tests use temporary directories.

Configuration installation and restoration stage complete copies beside each
destination, then use Linux atomic directory exchange for existing targets.
Hyprland's file watcher can reload during installation without encountering a
temporarily missing `hyprland.lua`. If the filesystem cannot exchange targets,
replacement fails with the existing configuration still present.

The interactive menu offers only core plus capture, animated wallpapers and
hardware tools. Every optional group defaults off. Existing application-group
flags remain available explicitly. No terminal UI framework is required.

Wallpaper downloads are opt-in (`--wallpapers` / `--no-wallpapers`), independent
of `--yes`. Supported media from the external repository's `wallpapers/` folder
is added to `~/Pictures/Wallpapers`; videos go in `animated/`. Existing files are
never overwritten. Restore removes only unchanged files added by the importer.
Legacy bundled-wallpaper records remain restorable. The old bundled source
directory is no longer required. Download failures show a retry command and do
not prevent configuration installation. Dry runs never download the collection.

Updates apply the current checkout; download changes from your own remote
separately with `git pull --ff-only` after committing local repository work.
Every update defaults to core; previously saved optional groups are not reused.
Feature flags and wallpaper downloads require explicit opt-in on each run. It tracks each
owned file's source and installed fingerprints, including locally compiled shader
outputs. Local-only edits and deletions remain intact. Conflicting incoming files
are saved under `danshell-installer/updates/<run>/incoming/`; exit status 2 means
local conflicts were preserved. Edited older installations without a recoverable
baseline retain their entire directory for manual reconciliation.

Each changed target has a previous copy under the update run's `before/` folder.
`restore` continues to restore the original pre-install backups. Dry runs do not
write metadata, backups, review files or configuration. A concurrent config change
stops publication rather than overwriting the newer edit.

Config targets are discovered from top-level files and directories in `config/`,
excluding repository metadata. Updates can add newly supplied targets to an older
installation, preserving conflicting existing app files and backing up the
original directory before adoption. Standalone files have the same update and
restore guarantees. Previously managed targets removed from the checkout remain
installed and can still be restored.

GTK 3/4, Neovim and Yazi configs are included in the config copy. Their theme
references point at the existing `danshell` palette output. Optional application
packages remain opt-in through `--groups terminal-apps`; this also includes Git,
fzf, ripgrep and mpv for the supplied editor and file-openers. Neovim plugin
installation remains its own first-launch operation.

The Spotify/Spicetify, VSCodium, Vesktop and Zen installation groups have been
removed from both package lists and dependency metadata. Existing application
installations and theme integrations are unchanged.

Fresh installs can install Hyprland as a core package. A normal Arch/CachyOS user
with sudo, working networking and a systemd user session is required; GPU drivers,
the OS and the login manager remain the machine's setup responsibility. If Python
is absent, the shell wrapper offers a core-only Python bootstrap; dry runs,
checks and recovery commands do not install it. Source validation runs both Qt's
parser and `Hyprland --verify-config` in an isolated temporary home.

`../uninstall.sh` uses the same recorded backups as restore, with wallpapers kept
by default. `--remove-wallpapers` explicitly includes unchanged tracked imports.
It does not require source configs or package metadata. Local edits retained by
an update are preserved too, and every required backup is checked before any
restoration. Installed packages, services and personal runtime state are kept.
