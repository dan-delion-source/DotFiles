-- Separate pre-login compositor. Never load the desktop user's configuration.
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.config({ misc = { disable_hyprland_logo = true, disable_splash_rendering = true },
            input = { kb_layout = "us" }, animations = { enabled = false } })
hl.on("hyprland.start", function()
    hl.exec_cmd("/usr/local/share/yozora-greeter/run-ui.sh")
end)
