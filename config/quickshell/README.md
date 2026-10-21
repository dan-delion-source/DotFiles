# Personal QuickShell configuration

An unbranded shell with an editable bar, control center, desktop widgets, and games. The internal identifier is `danshell`. The application dock and upstream updater/restore controls have been removed.

## Launch this checkout

From this directory:

```sh
./scripts/shell-control.sh start
./scripts/shell-control.sh restart
./scripts/shell-control.sh stop
```

The script resolves this checkout's absolute path. Restart reloads only this configuration through IPC, starting it if it is not running. Stop selects only this config. For foreground logs, use `qs --path /absolute/path/to/this/quickshell`.

Nothing is installed into `~/.config` automatically. Repository Hyprland modules use the sibling shell script and register shortcuts under `danshell:`; the settings window uses `org.danshell`. These changes take effect only when those Hyprland modules are loaded.

This remains an in-place, root-level configuration. QuickShell's root `shell.qml` takes precedence over named-config discovery, so use explicit `--path` arguments when selecting this or another config. Do not merge or overwrite sibling configs to launch this one.

File storage and process selection are isolated. Two complete desktop shells can still compete for the notification bus, session lock, wallpaper, or compositor-wide settings. Use one full shell per desktop session; this change does not attempt to virtualize those shared system services.

## Network Manager

- The control centre's top row includes **Network Manager**, alongside Games and Settings. Click it to open a separate island panel showing the current Wi-Fi or Ethernet connection and nearby Wi-Fi networks.
- Press **Test** in that panel to measure internet download and upload speed. The test never starts automatically. It transfers up to 48 MB against Cloudflare's speed-test service, and reports an estimate in Mbps for that route. You can cancel or repeat it.
- In **Settings → Control Centre**, arrange the top-row Network Manager button. A separate Network shortcut block is available in the grid editor if you want one there too.

## App launcher

- **Settings → Launcher → Results → List all apps** is on by default. It shows every launchable desktop entry alphabetically, with a scrollbar; typing searches the full list.
- Turn it off to use the existing **By use** or **Alphabetical** order and the configured **Results shown** limit. With it on, that slider controls how many rows fit on screen before scrolling.

## Fastfetch greeting

In **Settings → Appearance → Theme → Greeting**, select one of the existing palette scenes or the supplied **Arch** text logo and **Cat** animated GIF. Selecting a tile saves the choice and updates this checkout's `fastfetch/config.jsonc` logo type and source. The supplied files stay in `fastfetch/logos/`. Install or otherwise select this checkout's Fastfetch config for the choice to appear in your terminal; the QuickShell setting does not replace a separate live Fastfetch config.

## Network Speed

- In **Settings → Bar → Modules**, drag **Network Speed** into either bar zone. Both download and upload rates show by default; a per-module Figure override can hide them or show them on hover.
- In the **Control centre** layout editor, add **Network Speed** as a `2×1` rate display or `2×2` display with history graphs. It is independent of the existing Network connection controls.
- Click the bar module for both rates and five minutes of history. The existing sampler updates every three seconds; it does not perform a bandwidth speed test or make network requests.
- Measurements sum non-loopback interfaces. VPN, bridge, and virtual-interface traffic may be counted at multiple interfaces. Interface additions/removals and counter resets do not produce artificial spikes.
- Waiting and unavailable states replace stale figures. An idle valid sample displays `0 B/s`.

Both layout editors retain their normal move/remove behavior. Layouts and launcher favorites persist across reloads. The former branded control-center tile is now **System Info**.

## Storage and compatibility

The shell starts with fresh defaults and does not import existing settings, pets, notes, or game progress:

- State: `${XDG_STATE_HOME:-~/.local/state}/danshell`
- Data: `${XDG_DATA_HOME:-~/.local/share}/danshell`
- Cache: `${XDG_CACHE_HOME:-~/.cache}/danshell`
- Runtime: shell-owned files use the `danshell` directory or filename prefix under `XDG_RUNTIME_DIR`.

QuickShell also maintains its own instance registry; launch/IPC commands select this configuration explicitly. Existing backup directories are historical copies and are not rewritten or loaded by the active shell.

Original source attribution and the GPL license remain in the source, `NOTICE`, and `LICENSE`. Existing system avatar/face-unlock helper and PAM names are retained for compatibility; these are installed system interfaces, not visible shell branding. Face setup is managed externally rather than through the removed upstream installer. The installed cursor seed and read-only cursor source can be reused, while generated cursor themes and state use the new namespace. No system helper or original state directory is modified by this conversion.

Wallpaper and appearance actions retain the existing integrations with other desktop applications. Choosing them can still change those applications' themes.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
```

Regression tests cover traffic rates, loopback exclusion, interface churn/reset, and config-specific launch/reload/stop commands. Validation also included parsing changed QML and Lua files, compiling the shell against the installed Wayland backend without instantiating it, and an isolated offscreen widget/settings test. A full live-desktop drag/drop and multi-monitor test has not been performed.
