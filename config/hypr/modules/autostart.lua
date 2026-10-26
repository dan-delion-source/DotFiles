-- ╭──────────────────────────────────────────────────────────────────────────╮
-- │                                                                          │
-- │   A U T O S T A R T                                                      │
-- │   processes launched with the session                                    │
-- │                                                                          │
-- │   github.com/andreumassanet/impasto                                      │
-- │                                                                          │
-- ╰──────────────────────────────────────────────────────────────────────────╯

-- https://wiki.hypr.land/Configuring/Basics/Autostart/

-- Start only this installation's shell, including custom XDG config paths.
-- QuickShell owns notifications; a separate notification daemon is not needed.
hl.on("hyprland.start", function()
    hl.exec_cmd(require("modules.shell").command .. " start")
    hl.exec_cmd("awww query >/dev/null 2>&1 || awww-daemon")
end)

-- Reload only plugins already installed by the user.
hl.on("hyprland.start", function()
    hl.exec_cmd('test ! -d "/var/cache/hyprpm/$USER" || hyprpm reload')
end)

-- Standard polkit dialog for mounting devices and privileged operations.
hl.on("hyprland.start", function()
    hl.exec_cmd("test ! -x /usr/lib/polkit-kde-authentication-agent-1 || /usr/lib/polkit-kde-authentication-agent-1")
end)
