-- Yozora: fixed global workspace numbers, with a connected-monitor fallback.
-- Edit these two outputs when using a different monitor pair.
local M = {
    internal = "eDP-1",
    external = "HDMI-A-5",
}

function M.monitor_for(index)
    if index < 1 or index > 10 then return nil end
    local wanted = index <= 5 and M.internal or M.external
    local monitors = hl.get_monitors() or {}
    for _, monitor in ipairs(monitors) do
        if monitor.name == wanted then return wanted end
    end
    -- An unplugged HDMI display must not make its workspaces inaccessible.
    return monitors[1] and monitors[1].name or nil
end

function M.focus(index)
    -- No on_current_monitor: selecting a number goes to its assigned display.
    hl.dispatch(hl.dsp.focus({ workspace = index }))
end

function M.move_window(index)
    hl.dispatch(hl.dsp.window.move({ workspace = index, follow = true }))
end

function M.rehome()
    for _, workspace in ipairs(hl.get_workspaces() or {}) do
        local output = M.monitor_for(workspace.id)
        if output and workspace.monitor and workspace.monitor.name ~= output then
            hl.dispatch(hl.dsp.workspace.move({ workspace = workspace.id, monitor = output }))
        end
    end
end

for index = 1, 10 do
    hl.workspace_rule({
        workspace = tostring(index),
        monitor = index <= 5 and M.internal or M.external,
        persistent = true,
        default = index == 1 or index == 6,
    })
end

hl.on("hyprland.start", M.rehome)
hl.on("config.reloaded", M.rehome)
hl.on("monitor.added", M.rehome)

return M
