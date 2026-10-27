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

function M.cycle_used(direction, offer_empty)
    local active = hl.get_active_workspace()
    if not active or not active.monitor or direction == 0 then return end

    local occupied, used = {}, {}
    for _, workspace in ipairs(hl.get_workspaces() or {}) do
        if workspace.id > 0 and (workspace.windows or 0) > 0
            and workspace.monitor and workspace.monitor.name == active.monitor.name then
            table.insert(occupied, workspace.id)
            used[workspace.id] = true
        end
    end
    if #occupied == 0 then return end
    table.sort(occupied)

    -- Swipes offer one free slot after the last occupied workspace. An unused
    -- slot returns to the beginning on the next forward swipe; it never starts
    -- a chain of empty workspaces. The wheel keeps occupied-only navigation.
    if offer_empty and direction > 0 then
        if not used[active.id] then
            if active.id ~= occupied[1] then M.focus(occupied[1]) end
            return
        end
        if active.id == occupied[#occupied] then
            -- Prefer the next free number, then any earlier free slot if the
            -- monitor's range ends here. Never borrow another display's slot.
            for offset = 1, 10 do
                local index = (active.id + offset - 1) % 10 + 1
                if not used[index] and M.monitor_for(index) == active.monitor.name then
                    M.focus(index)
                    return
                end
            end
        end
    end

    -- Wrap on this monitor without entering another monitor's workspace set.
    local target = direction > 0 and occupied[1] or occupied[#occupied]
    if direction > 0 then
        for _, index in ipairs(occupied) do
            if index > active.id then target = index; break end
        end
    else
        for index = #occupied, 1, -1 do
            if occupied[index] < active.id then target = occupied[index]; break end
        end
    end
    if target ~= active.id then M.focus(target) end
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
