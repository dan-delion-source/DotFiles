# DotFiles

A personal CachyOS/Arch rice built around Hyprland and QuickShell. The goal is a
cohesive desktop that can be installed on another machine and adjusted from
QuickShell settings. Screenshots and references guide its own visual direction.

The shell and parts of the compositor configuration derive from
[Impasto by Andreu Massanet](https://github.com/andreumassanet/impasto).
Original attribution and GPLv3 terms remain in
[NOTICE](config/quickshell/NOTICE) and [LICENSE](config/quickshell/LICENSE).
`danshell` is the internal configuration/state identifier.

## Current setup

- QuickShell supplies the bar, control centre, launcher, notifications, lock
  screen, desktop widgets, settings and games. Noctalia is no longer used.
- Matugen generates dark tonal-spot colours from the selected wallpaper.
  Existing preset palettes remain available in the same appearance panel.
- Both colour modes use QuickShell's shared publisher for Kitty, GTK/Qt and
  supported application themes. Matugen runs without independent template hooks,
  avoiding competing colour writers.
- Hyprland defaults use preferred display modes, automatic positioning and
  automatic scaling. No connector names or personal workspace assignments ship
  in the defaults. Numbered workspace shortcuts remain available on any display.
- Wallpapers ship in `Wallpapers/`; the installer copies them to the XDG data
  directory's `wallpapers/` folder (about 420 MB).

## Requirements

Start with an installed CachyOS/Arch desktop running Hyprland. This installer
does not install an operating system, display manager, GPU drivers or Hyprland.
Use your desktop account, without running the script under `sudo`.

Compatibility floor: Hyprland **0.56.2**, QuickShell **0.3.2** and Matugen **4.0**.
These match the APIs used here; merely having a package with the right name is
insufficient. Required QML modules, Qt 6 syntax tooling and executable commands
are checked before configuration replacement. Python backend dependencies are
from the standard library; no pip environment is required.

The full dependency inventory is [install/dependencies.json](install/dependencies.json).
Official package availability is checked against configured pacman databases.
Missing candidates are verified against the AUR RPC; selected AUR packages need
an existing `paru` or `yay`. Repository metadata should be current. Installation
uses `pacman -Syu --needed` when repository packages are needed, so review the
system upgrade shown by pacman. AUR review and package-manager prompts remain
interactive, including with `--yes`.

## Check and install

```sh
# Read-only inventory, compatibility and service checks.
./install.sh check

# Preview package, service and configuration changes without writing anything.
./install.sh install --dry-run

# Choose optional groups interactively, review the plan, then install.
./install.sh install

# Preview a specific selection.
./install.sh install --groups capture,hardware,terminal-apps --dry-run

# Install that selection after confirmation.
./install.sh install --groups capture,hardware,terminal-apps
```

`check` exits nonzero for missing dependencies, incompatible tooling, inactive
required services or unavailable service checks. A dry run is a preview, not a
claim that packages have been installed or that a desktop session works.

| Optional group | Adds |
| --- | --- |
| `capture` | Satty, English OCR and wf-recorder |
| `animated` | mpvpaper animated wallpapers |
| `hardware` | DDC monitor brightness and power profiles |
| `terminal-apps` | btop, Yazi, Neovim and imv |
| `chat` | Vesktop |
| `music` | Spotify and Spicetify |
| `editor` | VSCodium |
| `browser` | Zen browser |
| `kde` | KDE theme tools |
| `thunar` | Thunar settings tools |

Core includes QuickShell, Matugen, Kitty, Thunar, Fastfetch, wallpaper/capture
utilities, fonts, emoji data, audio/network/Bluetooth tools, portals, a polkit
agent and theme support. A default browser should already be configured through
`xdg-settings`. Optional applications already installed may receive the shell's
existing theme integrations when changing colours.

The installer displays required service actions and requests confirmation before
enabling them. It refuses to start NetworkManager over an active systemd-networkd
setup, and refuses the power-profile group when TLP is active. Other existing
desktop/session integrations should be reviewed in the displayed plan.

Installation copies `hypr`, `quickshell`, `kitty`, `fastfetch`, and `matugen` into
the XDG config directory. Existing target directories, including old Hyprland
configuration files, are backed up before replacement. Existing wallpapers at
the target are also backed up. Copies keep the installed desktop independent of
the checkout. No shell is launched and no compositor reload is requested;
activate the configuration at your next Hyprland login. Run one full desktop
shell per session to avoid notification, lock and wallpaper service conflicts.

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

Use **Theme and wallpaper** to choose Matugen or a preset. The first bundled
wallpaper is the fresh-install fallback. Matugen failure retains the last valid
palette and displays a recovery message. Kitty reads generated palette/font
fragments through local links to the shell's XDG state directory.

Settings, notes and game progress stay in the shell's XDG directories under
`danshell`; another user's state is never copied from this repository. Optional
face-unlock/shared-avatar helpers and compositor plugins are detected if already
installed, but their system helpers, PAM stacks and plugins are not installed
here. Ordinary password unlocking uses the existing `login` PAM service.

## Restore and update

```sh
./install.sh restore --dry-run
./install.sh restore
```

Installer records and backups live under
`${XDG_STATE_HOME:-~/.local/state}/danshell-installer/`. Restore recovers original
configs and wallpapers. If an installed directory changed, its current contents
are preserved under `preserved/` before the original is restored. Packages,
enabled services, shell runtime state and application themes generated after
login are not reverted by config restoration.

Reinstalling identical files is a no-op. A source update can replace unchanged
installed files while retaining the original backup. If you or QuickShell have
modified an installed directory, installation stops: restore first, review the
preserved copy, then reinstall. Configuration copies are not automatically synced
back to the repository.

Custom XDG destinations can be selected with `--config-dir`, `--data-dir` and
`--state-dir`; use the same paths for restore. Destinations that overlap the
checkout or each other are rejected.

## Validation status

```sh
python3 -B -m unittest discover -s install/tests -v
python3 -B -m unittest discover -s config/quickshell/tests -v
```

Tests cover installation/reinstallation, original backups, preserved edits,
symlinks, interrupted copies, dependency selection, monitor-rule detection and
application, Matugen parsing/failure recovery, network sampling and manual speed
tests. Local validation includes real Matugen generation and Qt 6/Lua syntax
checks. Full desktop interaction, hotplug on physical hardware, and clean
CachyOS/Arch VM installations still need validation. The installer is an initial
implementation, not yet a verified cross-machine release.

References: [Hyprland Lua configuration](https://wiki.hypr.land/configuring/core/),
[Matugen usage](https://github.com/InioX/matugen/wiki/Usage).
