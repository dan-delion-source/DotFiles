import QtQuick
import QtTest
import "../../lock" as Lock
import "../../lock/LockStyles.js" as Styles

Item {
    width: 1280
    height: 720

    Lock.MainframeView {
        id: preview
        width: 1280
        height: 720
        preview: true
        motion: 0
        account: "Preview account"
        output: "DP-7"
    }

    Component {
        id: animatedView
        Lock.MainframeView { width: 800; height: 600; motion: 0.1 }
    }

    TestCase {
        name: "LockStyles"
        when: windowShown

        function cleanup() {
            preview.leaving = false
            preview.outro = 0
            preview.intro = 1
            preview.failed = false
            preview.authenticating = false
            preview.message = ""
        }
        function test_choices_and_safe_defaults() {
            compare(Styles.choices.length, 2)
            compare(Styles.normalize("mainframe"), "mainframe")
            compare(Styles.normalize("unknown"), "classic")
            compare(Styles.normalize(null), "classic")
        }
        function test_exit_deadline_and_disabled_motion() {
            compare(Styles.exitMs("classic", 1), 380)
            compare(Styles.exitMs("mainframe", 1), 1050)
            compare(Styles.exitMs("mainframe", 0), 0)
            compare(Styles.exitMs("mainframe", 100), 2100)
            compare(Styles.exitMs("mainframe", -1), 0)
            compare(Styles.exitMs("unknown", 1), 380)
        }
        function test_preview_is_still_and_cannot_authenticate() {
            compare(preview.intro, 1)
            compare(preview.outro, 0)
            compare(preview.passwordLength, 0)
            compare(typeof preview.submitted, "undefined")
            compare(typeof preview.lock, "undefined")
            compare(typeof preview.submit, "undefined")
        }
        function test_feedback_and_missing_capture() {
            compare(preview.shot.toString(), "")
            preview.message = "Wrong password"
            preview.failed = true
            compare(preview.statusText, "Wrong password")
            preview.message = ""
            preview.failed = false
            preview.authenticating = true
            compare(preview.statusText, "VERIFYING CREDENTIALS…")
            preview.authenticating = false
        }
        function test_no_motion_exit_is_immediate() {
            preview.leaving = true
            compare(preview.outro, 1)
            compare(preview.statusText, "ACCESS GRANTED")
            preview.leaving = false
        }
        function test_transition_timeline_completes() {
            const view = createTemporaryObject(animatedView, parent)
            verify(view !== null)
            tryCompare(view, "intro", 1, 800)
            view.leaving = true
            tryCompare(view, "outro", 1, 800)
        }
    }
}
