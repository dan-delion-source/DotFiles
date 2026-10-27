# Yozora

A personal CachyOS/Arch rice built around Hyprland and QuickShell. The goal is a
cohesive desktop that can be installed on another machine and adjusted from
QuickShell settings. Screenshots and references guide its own visual direction.

The shell and parts of the compositor configuration derive from
[Impasto by Andreu Massanet](https://github.com/andreumassanet/impasto).
Original attribution and GPLv3 terms remain in
[NOTICE](config/quickshell/NOTICE) and [LICENSE](config/quickshell/LICENSE).
Yozora is the rice name. Existing `danshell` storage and IPC identifiers are
retained for compatibility with saved settings, themes and game progress.

## Current setup

- QuickShell supplies the bar, control centre, launcher, notifications, lock
  screen, settings and games. Noctalia is no longer used.
- Matugen generates dark tonal-spot colours from the selected wallpaper.
  Existing preset palettes remain available in the same appearance panel.
- Both colour modes use QuickShell's shared publisher for Kitty, GTK/Qt and
  supported application themes. Matugen runs without independent template hooks,
  avoiding competing colour writers.
- Hyprland uses preferred display modes, automatic positioning and scaling.
  Workspaces 1–5 are assigned to `eDP-1`, and 6–10 to `HDMI-A-5`.
  `Super+1…9,0` selects the numbered workspace; adding Shift moves the active
  window there. `Super+mouse wheel` cycles only through occupied workspaces
  on the active monitor. Three-finger swipes also skip empty gaps, but offer
  one free workspace after the last occupied one. Leave it empty and the next
  forward swipe wraps to the first used workspace; open a window to keep it
  in the cycle. If the monitor's range is full, swipes wrap immediately.
  Swipes switch once per gesture; all workspaces remain accessible by number.
  If a monitor is disconnected, its workspaces remain accessible
  on an available display. Change the output names in
  `config/hypr/modules/workspaces.lua` for another monitor pair.
- Wallpapers are optional. The installer can download the external
  [wallpaper collection](https://github.com/dan-delion-source/Wallpapers) into
  `~/Pictures/Wallpapers`, which is also where the picker reads images. Videos
  go in its lowercase `animated/` subfolder. The picker updates automatically
  when files change. You can use your own images without downloading anything.

## Requirements

Start with an installed CachyOS/Arch system, working networking, configured GPU
drivers and a normal user account with sudo access. Run from that account's
systemd session, either a desktop terminal or a logged-in TTY. The installer can
install Hyprland and the core desktop packages when they are missing. It does
not install the operating system, GPU drivers or a display manager. Use your
desktop account, without running the script under `sudo`.

Compatibility floor: Hyprland **0.56.2**, QuickShell **0.3.2** and Matugen **4.0**.
These match the APIs used here; merely having a package with the right name is
insufficient. Required QML modules, Qt 6 syntax tooling, executable commands and the native
Hyprland Lua config parser are checked before configuration replacement. Python backend dependencies are
from the standard library; no pip environment is required. If Python is missing,
`install.sh` offers to install that required bootstrap dependency with
`sudo pacman -Syu --needed python` before showing the full installer plan.
Check, preview and recovery commands never bootstrap packages; install Python
manually first when using those commands on a minimal system.

Package names live in [packages/pacman.txt](packages/pacman.txt) and
[packages/aur.txt](packages/aur.txt), grouped by feature. Each line contains one
package. The AUR list contains only the main `matugen` package; there is no
`matugen-bin` alternative or optional app collection. The filenames describe expected sources; configured repositories are always
checked first. Command, service and compatibility metadata lives in
[install/dependencies.json](install/dependencies.json).
Official package availability is checked against configured pacman databases.
Missing candidates are verified against the AUR RPC; selected AUR packages need
an existing `paru` or `yay`. Repository metadata should be current. Installation
uses `pacman -Syu --needed` when repository packages are needed, so review the
system upgrade shown by pacman. AUR review and package-manager prompts remain
interactive, including with `--yes`.

## Check and install

```sh
# Numbered terminal menu: install, update, check, preview, restore or uninstall.
./install.sh

# Read-only inventory, compatibility and service checks.
./install.sh check

# Preview package, service and configuration changes without writing anything.
./install.sh install --dry-run

# Choose optional groups interactively, review the plan, then install.
./install.sh install

# Preview a specific selection, including optional wallpapers.
./install.sh install --groups capture,animated --wallpapers --dry-run

# Install core without the wallpaper collection.
./install.sh install --no-wallpapers

# Download/retry only wallpapers without replacing desktop configs.
./install.sh wallpapers
```

`check` exits nonzero for missing dependencies, incompatible tooling, inactive
required services or unavailable service checks. A dry run is a preview, not a
claim that packages have been installed or that a desktop session works.

| Interactive optional group | Adds |
| --- | --- |
| `capture` | Satty, English OCR and wf-recorder |
| `animated` | mpvpaper and FFmpeg for video posters |
| `hardware` | DDC monitor brightness and power profiles |

Every install and update defaults to core only. Spotify, Spicetify, VSCodium,
Vesktop and Zen package groups have been removed. Feature groups require a new
explicit selection on each run; previous optional selections are not reused.
`terminal-apps`, `kde` and `thunar` remain available only through explicit
`--groups` flags.
The standard Bluetooth, battery and backlight controls remain in core.

Copying an application's config does not install the application. To install the
optional terminal tools used by the Neovim and Yazi configs, select
`--groups terminal-apps`. This includes btop, Yazi, Neovim, imv, mpv, Git, fzf and
ripgrep. Language servers and extra parser build tools are not installed. The
supplied Neovim config downloads its plugins through lazy.nvim on first launch;
the installer does not launch it. Its generated theme reads the same `danshell`
state directory used by QuickShell, GTK and Yazi theme integration.

Core includes QuickShell, Matugen, Kitty, Thunar, Fastfetch, wallpaper/capture
utilities, fonts, emoji data, audio/network/Bluetooth tools, portals, a polkit
agent and theme support. A default browser should already be configured through
`xdg-settings`. Optional applications already installed may receive the shell's
existing theme integrations when changing colours.

The installer displays required service actions and requests confirmation before
enabling them. It refuses to start NetworkManager over an active systemd-networkd
setup, and refuses the power-profile group when TLP is active. Other existing
desktop/session integrations should be reviewed in the displayed plan.

Installation discovers the top-level files and directories in `config/` and
copies them into the XDG config directory. This includes `hypr`, `quickshell`,
`kitty`, `fastfetch`, `matugen`, `gtk-3.0`, `gtk-4.0`, `nvim` and `yazi`. New app
config directories and standalone config files are picked up automatically.
Repository metadata (`AGENTS.md`, `README.md`, `__pycache__`, `.git`, `.agents`,
`.codex`) is excluded. Existing target directories, including old Hyprland
configuration files, are backed up before replacement. Complete staged trees
are swapped atomically, so a watched config path never briefly disappears.
Filesystems must support Linux atomic directory exchange; a failed exchange
leaves the existing config in place. Copies keep the installed desktop independent
of the checkout. No shell is launched and no compositor reload is requested;
activate the configuration at your next Hyprland login. Run one full desktop
shell per session to avoid notification, lock and wallpaper service conflicts.

## Optional wallpaper collection

During an interactive install, the collection is offered with a default of **No**.
It may be a large download. A shallow clone is made in a temporary directory;
only supported media from its `wallpapers/` directory is copied to
`~/Pictures/Wallpapers`. Git metadata and README files are not copied. Existing
identical files and filename conflicts are skipped, with counts shown at the end.
No existing library is replaced. `git` is needed only when downloading.

Use `--wallpapers` to opt in explicitly or `--no-wallpapers` to skip the prompt.
`--yes` alone never opts into wallpapers. A failed optional download is reported
with `./install.sh wallpapers` as the retry command; it does not block desktop
installation. Neither check nor dry-run clones the collection or changes files.

The installer uses the Python standard library, with no additional terminal UI
packages. Colours are disabled for redirected output, `TERM=dumb`, or `NO_COLOR`.

## Wallpaper troubleshooting

The installer checks the daemon in a Wayland session and distinguishes an
unavailable daemon from a missing executable or running outside the session.
If the picker cannot apply an image, it keeps the last successful selection and
shows the error rather than saving the failed choice or changing its palette.

```sh
awww query
# If unavailable, run this in a terminal and inspect any errors:
awww-daemon
```

Hyprland already starts the daemon at login. A reload alone does not rerun its
login hook. No extra wallpaper daemon or system service is installed.

## Adjust another machine

Open QuickShell **Settings → Monitors** to choose resolution, refresh rate,
scale, arrangement and primary display. The bar follows that primary. Saved
arrangements are associated with the connected displays and reapplied on
reconnection; new setups fall back to automatic defaults. Input, appearance,
shortcuts and bar modules have their existing settings pages.

Battery, Bluetooth, audio and brightness controls use detected capabilities;
missing hardware displays unavailable states. External brightness also needs
monitor DDC/CI support and I2C permissions. The installer does not change kernel
module or user-group configuration for DDC.

Use **Theme and wallpaper** to choose Matugen or a preset. The first image in your library is the fresh-install fallback; an empty library
is allowed when you skip the download. Matugen failure retains the last valid
palette and displays a recovery message. Kitty reads generated palette/font
fragments through local links to the shell's XDG state directory.

Choose **Classic** or **Mainframe** under **Settings → Session → Lock screen**.
The choice is saved and applies to the next lock without restarting the shell.
Classic is the default; Mainframe adds the CRT terminal appearance using the
same authentication service. Settings previews never lock or authenticate.
See the [shell README](config/quickshell/README.md#lock-screen-styles) for details.

Settings, notes and game progress stay in the shell's XDG directories under
`danshell`; another user's state is never copied from this repository. Optional
face-unlock/shared-avatar helpers and compositor plugins are detected if already
installed, but their system helpers, PAM stacks and plugins are not installed
here. Ordinary password unlocking uses the existing `login` PAM service.

## Update an existing installation

Use **Update existing installation** in `./install.sh`, or run:

```sh
# After downloading changes into this checkout, preview and apply them.
./install.sh update --dry-run
./install.sh update
```

If you installed with the older installer, run `update` once now, before fetching
new versions, to establish per-file tracking while the original checkout is
still available. An update with no incoming changes keeps your config files as
they are and upgrades only the installer record.

To download future commits from your own configured DotFiles remote, commit your
local repository work first, then use `git pull --ff-only`. The updater applies
this checkout; it does not pull, reset, stash or copy anything from Impasto.

Updates also discover newly added config targets, so an existing installation
can receive the GTK, Neovim and Yazi configs without reinstalling the desktop.
For a newly managed app directory, existing files are kept, matching incoming
files are adopted, and conflicting incoming files are saved for review. The
original directory is backed up before it is adopted. Removing a whole app
config from the checkout leaves its installed copy in place and restorable.

Updates default to core only, regardless of previously saved feature groups. Add
`--groups capture,animated` on a run to enable those groups explicitly. Wallpaper
downloads remain opt-in; existing wallpapers and runtime settings are kept.

The updater compares each file with its last installed version. Unchanged files
receive updates; local-only edits, additions and deletions are preserved. Files
removed upstream are deleted only when still unmodified locally. A file changed
both locally and upstream stays in place; the incoming version is saved under
`~/.local/state/danshell-installer/updates/<run>/incoming/`, with deletion notes
in `conflicts/`. Conflicts produce exit status **2** so scripts can detect a
partially applied update. Accepting the incoming version at its live path and
rerunning update resolves that conflict; intentionally keeping a divergent local
version continues to report it on later updates.

Before replacing a directory, its current contents are copied to the run's
`before/` folder. The original pre-install backups are retained separately.
Config trees are published atomically using the same replacement step as install.
If a file changes between preview and publication, the updater stops; close the
application writing it and preview again. Updates do not explicitly reload the
shell or compositor; log out and back into Hyprland when ready to activate them.

Older records are migrated to per-file tracking when their baseline can be
identified. If both the old installed directory and checkout changed and that
baseline is unavailable, the whole live directory is kept and the incoming tree
is saved for review. An existing config not managed by this installer must first
be backed up and adopted through `./install.sh install`.

## Uninstall the configs

```sh
# Review what will be restored; does not change anything.
./uninstall.sh --dry-run

# Restore original config backups, preserving later edits separately.
./uninstall.sh

# Explicitly remove unchanged installer-added wallpapers as well.
./uninstall.sh --remove-wallpapers
```

`./install.sh uninstall` and the menu's **Uninstall configs** action are aliases.
The standalone script uses only Python and installer records; it works even if
`config/`, package lists or desktop dependencies have been removed. Use the same
`--config-dir`, `--data-dir` and `--state-dir` flags as the original install when
you chose custom destinations.

The uninstaller restores pre-install config directories, or removes configs
created by the installer when there was no original. Any edits or additional
files, including edits retained by an update, are preserved under
`~/.local/state/danshell-installer/preserved/` before restoring originals.
All required backups are checked before any config is touched. An interrupted
operation can be retried using the remaining records.

By default, it keeps wallpapers, installed packages, enabled services, notes,
game saves and other shell runtime state. `--remove-wallpapers` removes only
unchanged tracked imports; personal or edited images stay in place. Wallpaper
ownership records remain available for that later cleanup. It does not stop the
running shell; log out and back in after uninstalling. On a fresh install with
no previous configs, choose or configure the desktop you want to use next.

## Restore original configurations

```sh
./install.sh restore --dry-run
./install.sh restore
```

Installer records and backups live under
`${XDG_STATE_HOME:-~/.local/state}/danshell-installer/`. Restore recovers original
configs and legacy bundled wallpapers. New wallpaper imports are tracked per
file: restore removes only unchanged installer-added files and leaves edited or
pre-existing images in place. If an installed config directory changed, its current contents
are preserved under `preserved/` before the original is restored. Packages,
enabled services, shell runtime state and application themes generated after
login are not reverted by config restoration.

Reinstalling identical files is a no-op. Use `update` for subsequent changes,
especially when you or QuickShell modified an installed directory. `restore`
returns to the original pre-install configuration, rather than the immediately
previous update. Previous update copies are available in each run's `before/`
folder. Configuration copies are not automatically synced back to the repository.

Custom XDG destinations can be selected with `--config-dir`, `--data-dir` and
`--state-dir`; use the same paths for update and restore. Destinations that overlap the
checkout or each other are rejected.

## Validation status

```sh
python3 -B -m unittest discover -s install/tests -v
python3 -B -m unittest discover -s config/quickshell/tests -v
```

Tests cover Python bootstrap/cancellation, missing-Hyprland installation, the
full shipped-config copy and native shader build, standalone uninstallation
without source configs, menu options, optional defaults, package lists, wallpaper download failure,
conflicting filenames, imported-file restoration, daemon/application failures,
installation/reinstallation, per-file updates, local conflicts and deletions,
legacy update records, original backups, preserved edits,
symlinks, interrupted copies, dependency selection, monitor-rule detection and
application, Matugen parsing/failure recovery, network sampling and manual speed
tests. Local validation includes real Matugen generation, Qt 6 checks and Hyprland's
native `--verify-config` parser. Core package names were checked against the
configured local pacman repository databases. Isolated tests do not prove a GPU
login or fresh package downloads on another machine. Full desktop interaction, hotplug on physical hardware, and clean
CachyOS/Arch VM installations still need validation. Use this updated checkout when testing another machine. Commit and push the new
config directories, assets, scripts and package lists before cloning it elsewhere;
untracked local files are not included in a Git clone.

References: [Hyprland Lua configuration](https://wiki.hypr.land/configuring/core/),
[Matugen usage](https://github.com/InioX/matugen/wiki/Usage).
