# Yozora QuickShell

Yozora is a shell with an editable bar, control center, and games. The existing internal `danshell` identifier is retained for saved-data and shortcut compatibility. The application dock and upstream updater/restore controls have been removed.

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

In **Settings → Appearance → Theme → Greeting**, select a palette scene or a logo from this checkout's `fastfetch/logos/` folder (`~/.config/fastfetch/logos` when installed). TXT, PNG, JPG/JPEG, WebP and GIF files appear with previews and filename labels. The supplied **Arch** and **Cat** choices remain available when their files are present. After adding, removing or replacing files, click **Settings → System → Profiles → Library updates → Update Greeter**. The list also loads at startup; it is not watched automatically. Refreshing keeps your current selection. Selecting a tile saves the choice and updates this checkout's `fastfetch/config.jsonc` logo type and source without replacing your Fastfetch modules.

For Zsh, source `"${XDG_CONFIG_HOME:-$HOME/.config}/fastfetch/greeting.zsh"` from `.zshrc`. `fa` follows the saved choice; `fa koi`, `fa arch`, `fa cat`, and `fa random` override it for one invocation. The helper passes the matching text/image renderer explicitly and uses `danshell` state, so a previous Arch selection cannot make a GIF render as text. Run `fa` instead of bare `fastfetch` in terminal startup if you want Random to pick a new scene each time. Missing generated scenes are initialized on first use.

## Wallpaper library

The bar's Appearance picker reads still images from **`~/Pictures/Wallpapers`** and animated wallpapers from **`~/Pictures/Wallpapers/animated`**. Still formats are JPG/JPEG, PNG and WebP; animated formats are MP4, WebM, MKV, MOV and GIF. Folder names are case-sensitive. Files are read directly, not copied or moved. The library refreshes automatically when files are added, removed, renamed or replaced, including while the picker is open. Changes update the choices without applying another wallpaper. Hidden and unsupported files are ignored. A missing folder gives an empty list and is watched for recreation. The older `~/.local/share/wallpapers` collection is no longer used for discovery.

## Network Speed

- In **Settings → Bar → Modules**, drag **Network Speed** into either bar zone. Both download and upload rates show by default; a per-module Figure override can hide them or show them on hover.
- In the **Control centre** layout editor, add **Network Speed** as a `2×1` rate display or `2×2` display with history graphs. It is independent of the existing Network connection controls.
- Click the bar module for both rates and five minutes of history. The existing sampler updates every three seconds; it does not perform a bandwidth speed test or make network requests.
- Measurements sum non-loopback interfaces. VPN, bridge, and virtual-interface traffic may be counted at multiple interfaces. Interface additions/removals and counter resets do not produce artificial spikes.
- Waiting and unavailable states replace stale figures. An idle valid sample displays `0 B/s`.

Both layout editors retain their normal move/remove behavior. Layouts and launcher favorites persist across reloads. The former branded control-center tile is now **System Info**.

## Bar position

Open **Settings → Bar & Island → The island → Position** to select **Top**,
**Left**, **Right** or **Bottom**. The choice takes effect immediately and is
saved with profiles. Top remains the default for existing settings.

With Left or Right selected, **The island → Scale → Side bar width** adjusts
the width independently of bar height (30–120 px, default 56 px). Modules,
input regions, panel offsets and reserved screen space follow the width.
Bar height ranges from 24–48 px. Smaller saved values are raised to the
minimum when loaded.

Side bars stack upright module icons, gauges, figures, workspace markers and
tray icons. Transfer rates get separate upload/download lines. The editor's
left group goes above the clock and the right group below it; their saved order
stays the same. Scroll a group when it is longer than the available space.
Bottom bars stay horizontal and open panels upward; side panels open inward.
Panels stay inside the screen, with scrolling for oversized grids and games.
Appearance, wallpaper, palette and game pickers use portrait panels and
vertical carousels on side bars. Up/Down browse cards; in Appearance,
Left/Right switch animated wallpaper, wallpaper and palette sections. Mouse
wheel and click/Enter selection remain available. Game boards scale into a
portrait frame without changing their aspect ratio. Top/bottom bars retain
the horizontal pickers.

Grouped, Spread and One island styles remain available on every edge.
With Spread selected, **Spread background → Black band** adds a continuous
black background across the bar while keeping the spread layout, with 12 px
of padding at both ends and inset side-bar contents. Choose
**Floating** to return to separate capsules. The background option is hidden
and its band disabled in top-edge Notch mode; the saved choice returns when
switching back to a floating bar. The choice saves with profiles.
In Spread mode on a side bar, the centre clock is a taller column with stacked
hours and minutes, optional seconds and the optional date underneath. It
follows the existing 12/24-hour, seconds and date settings.
The notch option belongs to the top edge and is remembered when changing edges.
The compositor's reserved strip follows the selected position.

Position persistence, profile switching, rail layouts and popup geometry are
checked in isolation. Live compositor focus, edge switching and physical
multi-monitor behavior still need a desktop check after installation.

## Kanji workspace labels

The Kanji workspace style uses a bundled 6 KB numeral font, so it works without
Japanese system fonts. The same font is used in the bar and Settings preview;
other workspace styles keep the selected interface font. The asset is a renamed
Noto Sans JP subset under SIL OFL 1.1; source and rebuild instructions are in
`assets/fonts/README.md`.

## Desktop

Desktop widgets, their grid editor, widget themes and edge-note decks have been
removed. The wallpaper stays clear. Bar modules, control-centre blocks, notes
and games remain available. Shared weather, GitHub, pet-style and note-font
preferences are under **Settings → Bar & Island → Module settings**.
Old desktop placement fields are ignored when loading settings or profiles.

## Running cat

Open **Settings → Bar → Modules** and drag **Running Cat** from the catalogue
onto either side of the bar preview. Drag it again to reorder or move it to the
other side; remove it like any other module. Placement saves across reloads.
Existing saved layouts stay as you arranged them until you add the cat.

This uses Zenith Shell's exact four original PNG frames without recolouring.
Animation follows its power-profile timings: balanced 150 ms, performance
80 ms, turbo 50 ms, power saver 220 ms; unavailable profiles use 200 ms.
The cat runs in place in its module. Hidden modules and the global motion-off
setting pause it. It uses the existing system sampler and adds no dependencies.
It is separate from the existing Pet module. Asset provenance and the retained
Unlicense are in `assets/running-cat/` and `NOTICE`.

## Lock screen styles

Open **Settings → Session → Lock screen → Lock screen style** and choose
**Classic** or **Mainframe**. Selection saves immediately and takes effect on the
next lock without a shell restart. Classic remains the default. Clock and blur
controls appear for Classic and retain their previous values when hidden.

Mainframe adds a phosphor-cell clock, typed console text, CRT curvature and
scanlines, and line/dot entry and exit transitions. Colours follow the active
Matugen or preset palette. Iosevka Nerd Font is preferred, with an installed
monospace fallback. The existing motion control also applies; None disables
transitions and blinking. Both styles use the same password/optional face
unlock service, and a style is held constant across monitors for each lock.
The loader falls back to Classic if Mainframe cannot load.

Preview cards only draw: they have no password input, authentication or session
lock actions. Profiles include the selected style. Mainframe adapts the visual
direction and CRT shader from dhrruvsharma/shell; see NOTICE for attribution.

The installer includes Iosevka and Qt shader tooling, and bakes the supplied
shader source with the target system's `/usr/lib/qt6/bin/qsb` before replacing
configs. For a checkout, rebuild it with:

```sh
/usr/lib/qt6/bin/qsb --glsl '100 es,120,150' --hlsl 50 --msl 12 \
  -o lock/shaders/mainframe-crt.frag.qsb lock/shaders/mainframe-crt.frag
```

The offscreen tests exercise persistence, profiles, fallback, simulated display
surfaces, input clearing and exit timers without constructing a real session
lock or starting a PAM conversation. Software-rendered layout previews do not
verify GPU CRT effects or physical monitor hotplug. Those need a live desktop
check after installation.

## Storage and compatibility

The shell starts with fresh defaults and does not import existing settings, pets, notes, or game progress:

- State: `${XDG_STATE_HOME:-~/.local/state}/danshell`
- Data: `${XDG_DATA_HOME:-~/.local/share}/danshell`
- Cache: `${XDG_CACHE_HOME:-~/.cache}/danshell`
- Runtime: shell-owned files use the `danshell` directory or filename prefix under `XDG_RUNTIME_DIR`.

QuickShell also maintains its own instance registry; launch/IPC commands select this configuration explicitly. Historical development backups have been removed from this checkout; installation backups live outside the configuration.

Original source attribution and the GPL license remain in the source, `NOTICE`, and `LICENSE`. Existing system avatar/face-unlock helper and PAM names are retained for compatibility; these are installed system interfaces, not visible shell branding. Face setup is managed externally rather than through the removed upstream installer. The installed cursor seed and read-only cursor source can be reused, while generated cursor themes and state use the new namespace. No system helper or original state directory is modified by this conversion.

Wallpaper colours are generated by Matugen (dark tonal-spot); the existing preset palettes remain selectable. Both use the shared theme publisher, including Kitty's state fragments exposed as local config links. Generation failures retain the last valid palette and show a message in appearance settings. Wallpaper discovery uses the XDG data directory's `wallpapers` folder, populated by the root installer. The bar follows the primary display selected in Settings → Monitors instead of assuming a laptop connector.

Wallpaper and appearance actions retain the existing integrations with other desktop applications. Choosing them can still change those applications' themes. See the root README for installer and restoration boundaries.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
```

Regression tests cover traffic rates, loopback exclusion, interface churn/reset, and config-specific launch/reload/stop commands. Validation also included parsing changed QML and Lua files, compiling the shell against the installed Wayland backend without instantiating it, and an isolated offscreen widget/settings test. A full live-desktop drag/drop and multi-monitor test has not been performed.
