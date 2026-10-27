-- ╭──────────────────────────────────────────────────────────────────────────╮
-- │                                                                          │
-- │   K E Y B I N D S                                                        │
-- │   keyboard and mouse bindings                                            │
-- │                                                                          │
-- │   github.com/andreumassanet/impasto                                      │
-- │                                                                          │
-- ╰──────────────────────────────────────────────────────────────────────────╯

-- No bind uses /, ., ' or `: they are shifted or dead keys on a Spanish layout.

local apps    = require("modules.programs")
local mainMod = "SUPER"


-- ── PROFILE KEYS ────────────────────────────────────────────────────────────

-- The shell writes the active profile's bindings to keys.tsv
-- (description<TAB>combination, empty = unbound) and reloads Hyprland when
-- they change. Descriptions are the keys, so renaming one drops its binding
-- from every profile. The combinations below are the fallback.
local function profile_keys()
    local state = os.getenv("XDG_STATE_HOME") or (os.getenv("HOME") .. "/.local/state")
    local keys  = {}
    local file  = io.open(state .. "/danshell/keys.tsv")
    if not file then
        return keys
    end
    for line in file:lines() do
        local description, combination = line:match("^([^#\t][^\t]*)\t(.*)$")
        if description then
            keys[description] = combination
        end
    end
    file:close()
    return keys
end

local keys = profile_keys()

-- `hl.bind`, on the profile's combination for this description.
local function bind(combination, action, options)
    local chosen = keys[options.description]
    if chosen == nil then
        chosen = combination
    end
    if chosen ~= "" then
        hl.bind(chosen, action, options)
    end
end


-- ── BINDS ───────────────────────────────────────────────────────────────────

hl.config({
    binds = {
        workspace_back_and_forth = false,
    },
})


-- ── APPLICATIONS ────────────────────────────────────────────────────────────

bind(mainMod .. " + Return", hl.dsp.exec_cmd(apps.terminal),     { description = "Applications · Open a terminal" })
bind(mainMod .. " + E",      hl.dsp.exec_cmd(apps.file_manager), { description = "Applications · Open the file manager" })
bind(mainMod .. " + B",      hl.dsp.exec_cmd(apps.browser),      { description = "Applications · Open the browser" })


-- ── WINDOWS ─────────────────────────────────────────────────────────────────

-- · floating size
--
-- A floated window keeps its tiled size, which for a lone window is the whole
-- workspace. Float it at a fraction of the monitor instead, centred.
local FLOAT_FRACTION = 0.6

-- Resize and centre only when going tiled → floating; the state must be read
-- before the toggle.
local function float_centred()
    local window = hl.get_active_window()
    if not window then
        return
    end

    local was_floating = window.floating
    hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
    if was_floating then
        return
    end

    local monitor = hl.get_active_monitor()
    if not monitor then
        return
    end

    -- The monitor reports physical pixels; the dispatcher takes logical ones.
    local scale = monitor.scale or 1
    hl.dispatch(hl.dsp.window.resize({
        x     = math.floor(monitor.width / scale * FLOAT_FRACTION),
        y     = math.floor(monitor.height / scale * FLOAT_FRACTION),
        exact = true,
    }))
    hl.dispatch(hl.dsp.window.center())
end

-- The split is dwindle's. Master turns its stack to the next side instead;
-- scrolling has no split, and the key does nothing there.
local function flip_split()
    local workspace = hl.get_active_workspace()
    local layout = workspace and workspace.tiled_layout
    if layout == "dwindle" then
        hl.dispatch(hl.dsp.layout("togglesplit"))
    elseif layout == "master" then
        hl.dispatch(hl.dsp.layout("orientationnext"))
    end
end

bind(mainMod .. " + Q",           hl.dsp.window.close(), { description = "Windows · Close the focused window" })
bind(mainMod .. " + SHIFT + Q",   hl.dsp.window.kill(),  { description = "Windows · Kill the focused window" })
bind(mainMod .. " + F",           hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }), { description = "Windows · Full screen" })
bind(mainMod .. " + ALT + F",     hl.dsp.window.fullscreen({ mode = "maximized", action = "toggle" }),  { description = "Windows · Maximise, keeping the bar" })
bind(mainMod .. " + ALT + Space", float_centred,          { description = "Windows · Float or tile the window" })
bind(mainMod .. " + P",           hl.dsp.window.pseudo(), { description = "Windows · Toggle pseudo-tiling" })
bind(mainMod .. " + J",           flip_split,             { description = "Windows · Flip the split direction" })

-- · move focus
bind(mainMod .. " + left",  hl.dsp.focus({ direction = "l" }), { description = "Windows · Focus the window left" })
bind(mainMod .. " + right", hl.dsp.focus({ direction = "r" }), { description = "Windows · Focus the window right" })
bind(mainMod .. " + up",    hl.dsp.focus({ direction = "u" }), { description = "Windows · Focus the window up" })
bind(mainMod .. " + down",  hl.dsp.focus({ direction = "d" }), { description = "Windows · Focus the window down" })

-- · cycle windows
bind("ALT + Tab",         hl.dsp.window.cycle_next(),                 { repeating = true, description = "Windows · Next window" })
bind("ALT + SHIFT + Tab", hl.dsp.window.cycle_next({ next = false }), { repeating = true, description = "Windows · Previous window" })

-- · move the window itself
bind(mainMod .. " + SHIFT + left",  hl.dsp.window.move({ direction = "l" }), { description = "Windows · Move the window left" })
bind(mainMod .. " + SHIFT + right", hl.dsp.window.move({ direction = "r" }), { description = "Windows · Move the window right" })
bind(mainMod .. " + SHIFT + up",    hl.dsp.window.move({ direction = "u" }), { description = "Windows · Move the window up" })
bind(mainMod .. " + SHIFT + down",  hl.dsp.window.move({ direction = "d" }), { description = "Windows · Move the window down" })

-- · drag and resize with the mouse
bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true, description = "Windows · Drag the window" })
bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Windows · Resize the window" })


-- ── WORKSPACES ──────────────────────────────────────────────────────────────

local workspace_map = require("modules.workspaces")

-- Global numbers are stable across both screens; 0 is workspace 10.
for i = 1, 10 do
    local index = i
    local key = i % 10
    bind(mainMod .. " + " .. key, function() workspace_map.focus(index) end,
         { description = "Workspaces · Go to workspace " .. i })
    bind(mainMod .. " + SHIFT + " .. key, function() workspace_map.move_window(index) end,
         { description = "Workspaces · Move the window to workspace " .. i })
end

-- · scroll wheel skips empty workspaces on this screen
bind(mainMod .. " + mouse_down", function() workspace_map.cycle_used(1) end, { description = "Workspaces · Next occupied workspace" })
bind(mainMod .. " + mouse_up",   function() workspace_map.cycle_used(-1) end, { description = "Workspaces · Previous occupied workspace" })


-- ── SCREENS ─────────────────────────────────────────────────────────────────

-- · the keyboard, and the workspace under it, across screens. A window
-- · crosses with the window keys above: with nothing that way, they hand it
-- · to the next screen.

-- The two screens trade what they are showing, and the keyboard goes with the
-- workspace. Windows trade while workspace numbers keep their assigned
-- monitors. A missing screen in that direction leaves everything in place.
local function trade_workspace(direction)
    return function()
        local here = hl.get_active_monitor()
        if not here then
            return
        end

        hl.dispatch(hl.dsp.focus({ monitor = direction }))

        local there = hl.get_active_monitor()
        if not there or there.name == here.name then
            return
        end

        local from, to = here.active_workspace, there.active_workspace
        if not from or not to then
            return
        end
        local leaving  = hl.get_workspace_windows(from.id) or {}
        local arriving = hl.get_workspace_windows(to.id) or {}
        for _, window in ipairs(leaving) do
            hl.dispatch(hl.dsp.window.move({ workspace = to.id, window = "address:" .. window.address, follow = false }))
        end
        for _, window in ipairs(arriving) do
            hl.dispatch(hl.dsp.window.move({ workspace = from.id, window = "address:" .. window.address, follow = false }))
        end
    end
end

bind(mainMod .. " + ALT + left",          hl.dsp.focus({ monitor = "l" }), { description = "Screens · Focus the screen left" })
bind(mainMod .. " + ALT + right",         hl.dsp.focus({ monitor = "r" }), { description = "Screens · Focus the screen right" })
bind(mainMod .. " + ALT + SHIFT + left",  trade_workspace("l"), { description = "Screens · Take the workspace to the screen left" })
bind(mainMod .. " + ALT + SHIFT + right", trade_workspace("r"), { description = "Screens · Take the workspace to the screen right" })


-- ── MEDIA KEYS ──────────────────────────────────────────────────────────────

-- · volume and brightness; brightness goes through the shell, which knows
-- · the focused screen and how to dim it
bind("XF86AudioRaiseVolume",  hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true, description = "Media · Volume up" })
bind("XF86AudioLowerVolume",  hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),      { locked = true, repeating = true, description = "Media · Volume down" })
bind("XF86AudioMute",         hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true, description = "Media · Mute output" })
bind("XF86AudioMicMute",      hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),   { locked = true, description = "Media · Mute microphone" })
bind("XF86MonBrightnessUp",   hl.dsp.global("danshell:brightnessUp"),                          { locked = true, repeating = true, description = "Media · Brightness up" })
bind("XF86MonBrightnessDown", hl.dsp.global("danshell:brightnessDown"),                        { locked = true, repeating = true, description = "Media · Brightness down" })

-- · Acer laptops send XF86Launch6 for the microphone key
bind("XF86Launch6",           hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),   { locked = true, description = "Media · Mute microphone (Acer)" })

-- · player; distinct descriptions so each key can be rebound separately
bind("XF86AudioPlay",  hl.dsp.exec_cmd("playerctl play-pause"), { locked = true, description = "Media · Play or pause" })
bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true, description = "Media · Play or pause, from the pause key" })
bind("XF86AudioNext",  hl.dsp.exec_cmd("playerctl next"),       { locked = true, description = "Media · Next track" })
bind("XF86AudioPrev",  hl.dsp.exec_cmd("playerctl previous"),   { locked = true, description = "Media · Previous track" })


-- ── SESSION ─────────────────────────────────────────────────────────────────

-- · the power button opens the session menu instead of powering off (logind
-- · is told to ignore it, see system/etc/systemd/logind.conf.d/). Some
-- · machines never report a short press, so the menu has keyboard binds too.
bind(mainMod .. " + X",         hl.dsp.global("danshell:session"), { description = "Session · Session menu" })
bind("CTRL + ALT + Delete",     hl.dsp.global("danshell:session"), { description = "Session · Session menu, from CTRL + ALT + Delete" })
bind("XF86PowerOff",            hl.dsp.global("danshell:session"), { description = "Session · Session menu, from the power button" })
bind(mainMod .. " + L",         hl.dsp.global("danshell:lock"),    { description = "Session · Lock the screen" })
bind(mainMod .. " + SHIFT + E", hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"), { description = "Session · Exit Hyprland" })


-- ── UTILITIES ───────────────────────────────────────────────────────────────

-- · dpms actually powers the panel off, unlike brightness 0. Only this bind
-- · wakes it (key/mouse wake is off). The dispatcher toggles; it ignores
-- · a state argument.
bind(mainMod .. " + SHIFT + D", hl.dsp.dpms(), { locked = true, description = "Utilities · Turn the screen off or back on" })
bind(mainMod .. " + CTRL + R",  hl.dsp.exec_cmd(require("modules.shell").command .. " restart"), { description = "Utilities · Restart the shell" })


-- ── SHELL ───────────────────────────────────────────────────────────────────

-- · global shortcuts registered by the shell
bind(mainMod .. " + Space",     hl.dsp.global("danshell:launcher"),   { description = "Shell · Open the launcher" })
bind(mainMod .. " + A",         hl.dsp.global("danshell:controls"),   { description = "Shell · Open the control centre" })
bind(mainMod .. " + TAB",       hl.dsp.global("danshell:overview"),   { description = "Shell · Open the workspace overview" })
bind(mainMod .. " + comma",     hl.dsp.global("danshell:settings"),   { description = "Shell · Open settings" })
bind(mainMod .. " + T",         hl.dsp.global("danshell:appearance"), { description = "Shell · Open appearance" })
bind(mainMod .. " + SHIFT + T", hl.dsp.global("danshell:palette"),    { description = "Shell · Open the palette" })
bind(mainMod .. " + U",         hl.dsp.global("danshell:stats"),      { description = "Shell · Open system statistics" })
bind(mainMod .. " + SHIFT + P", hl.dsp.global("danshell:pet"),        { description = "Shell · Open the pet" })
bind(mainMod .. " + G",         hl.dsp.global("danshell:games"),      { description = "Shell · Open the games" })
bind(mainMod .. " + S",         hl.dsp.global("danshell:notes"),      { description = "Shell · Open the notes" })
bind(mainMod .. " + K",         hl.dsp.global("danshell:board"),      { description = "Shell · Open the task board" })

-- · key sheet, read from `hyprctl binds`. H, since / is SHIFT + 7 on a
-- · Spanish layout
bind(mainMod .. " + H",         hl.dsp.global("danshell:keys"),       { description = "Shell · Show every key" })

-- · zen: the bar away and its band to the windows; and the widgets away
bind(mainMod .. " + CTRL + B",  hl.dsp.global("danshell:zen"),        { description = "Shell · Hide or show the bar" })

-- · packages panel (pacman + AUR); installs run in a terminal
bind(mainMod .. " + I",         hl.dsp.global("danshell:packages"),   { description = "Shell · Open the packages" })

-- · clipboard history is a launcher mode
bind(mainMod .. " + V",         hl.dsp.global("danshell:clipboard"),  { description = "Shell · Open the clipboard history" })

-- · emoji, a launcher mode too
bind(mainMod .. " + period",    hl.dsp.global("danshell:emoji"),      { description = "Shell · Pick an emoji" })

-- · colour picker (hyprpicker); the result goes to the clipboard
bind(mainMod .. " + SHIFT + C", hl.dsp.global("danshell:picker"),     { description = "Shell · Pick a colour off the screen" })

-- · capture surface. The direct captures below are unbound by default and
-- · can be assigned in Settings → Keys.
bind(mainMod .. " + SHIFT + S", hl.dsp.global("danshell:capture"), { description = "Shell · Open the capture surface" })
bind("Print",                   hl.dsp.global("danshell:capture"), { description = "Shell · Open the capture surface, from Print" })
bind(mainMod .. " + SHIFT + R", hl.dsp.global("danshell:record"),  { description = "Shell · Start or stop recording the screen" })
bind("", hl.dsp.global("danshell:captureRegion"), { description = "Shell · Capture a region" })
bind("", hl.dsp.global("danshell:captureWindow"), { description = "Shell · Capture a window" })
bind("", hl.dsp.global("danshell:captureScreen"), { description = "Shell · Capture the whole screen" })
bind("", hl.dsp.global("danshell:captureEdit"),   { description = "Shell · Capture a region and annotate it" })
bind("", hl.dsp.global("danshell:captureText"),   { description = "Shell · Read a region as text" })


-- ── LID ─────────────────────────────────────────────────────────────────────

-- Plain `hl.bind`, not profile keys. Kept out of monitors.lua: a `switch:`
-- bind in the same file as `hl.monitor()` calls is silently never registered.
--
-- `switch:on` is the lid closing. `locked = true` so it also fires on the lock
-- screen. The shell decides what to do (Settings → Displays).
hl.bind("switch:on:Lid Switch",  hl.dsp.global("danshell:lidClosed"),
        { locked = true, description = "Session · The laptop lid was closed" })
hl.bind("switch:off:Lid Switch", hl.dsp.global("danshell:lidOpened"),
        { locked = true, description = "Session · The laptop lid was opened" })

-- Lid events go to the same monitor owner as settings and hotplug.
hl.bind("switch:on:Lid Switch", hl.dsp.global("danshell:lidClosed"), { locked = true, description = "Session · Lid closed" })
hl.bind("switch:off:Lid Switch", hl.dsp.global("danshell:lidOpened"), { locked = true, description = "Session · Lid opened" })
