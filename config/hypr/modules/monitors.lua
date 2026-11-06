-- ╭──────────────────────────────────────────────────────────────────────────╮
-- │                                                                          │
-- │   M O N I T O R S                                                        │
-- │   displays · resolution and layout                                       │
-- │                                                                          │
-- │                                                                          │
-- ╰──────────────────────────────────────────────────────────────────────────╯

-- https://wiki.hypr.land/Configuring/Basics/Monitors/
--
-- Per-setup arrangements are applied at runtime by the shell's
-- MonitorService, which keeps a profile for each set of connected screens.

hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})

-- Keep fullscreen video in the configured display colorspace. Automatic HDR
-- can enable wide gamut on an 8-bit output and trigger a 10-bit warning.
hl.config({
    render = {
        cm_auto_hdr = 0,
    },
})


-- Workspace ownership: 1–5 on eDP-1, 6–10 on HDMI-A-5.
require("modules.workspaces")

-- ── LID ─────────────────────────────────────────────────────────────────────

-- The lid switch binds are in keybinds.lua: a `switch:` bind declared in the
-- same file as `hl.monitor()` calls is silently never registered. They hand
-- the event to MonitorService, which updates the display profile, because
-- runtime monitor rules are dropped on every config reload.
