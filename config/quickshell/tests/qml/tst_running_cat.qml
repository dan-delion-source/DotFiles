import QtQuick
import QtTest
import "../../components" as Components

Item {
    width: 200; height: 100
    Components.RunningCat { id: cat; profile: "balanced" }

    TestCase {
        name: "RunningCat"
        when: windowShown

        function cleanup() {
            cat.visible = true
            cat.lively = true
            cat.paused = false
            cat.profile = "balanced"
        }
        function test_original_profile_timings() {
            const profiles = [["balanced", 150], ["performance", 80], ["turbo", 50],
                              ["powersave", 220], ["power-saver", 220], ["unknown", 200]]
            for (const row of profiles) {
                cat.profile = row[0]
                compare(cat.interval, row[1])
            }
        }
        function test_four_frames_loop_and_hidden_animation_pauses() {
            cat.profile = "turbo"
            const first = cat.frame
            tryVerify(() => cat.frame !== first, 400)
            for (let i = 0; i < 5; i++) {
                wait(60)
                verify(cat.frame >= 0 && cat.frame < 4)
            }
            cat.visible = false
            const frozen = cat.frame
            wait(130)
            compare(cat.frame, frozen)
            verify(!cat.animating)
        }
        function test_motion_off_and_pause_keep_sprite_still() {
            cat.lively = false
            verify(!cat.animating)
            const frozen = cat.frame
            wait(230)
            compare(cat.frame, frozen)
            cat.lively = true
            cat.paused = true
            verify(!cat.animating)
        }
    }
}
