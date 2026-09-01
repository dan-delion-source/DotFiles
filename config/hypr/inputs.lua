hl.config({
    input = {
        -- sensitivity = -0.25,
        accel_profile = "flat",

        touchpad = {
            natural_scroll = true
        }
    },
})

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
-- hl.gesture({ fingers = 3, direction = "down", action = "close" })
-- hl.gesture({ fingers = 3, direction = "up", action = "fullscreen" })
-- hl.gesture({ fingers = 3, direction = "left", action = "float" })
