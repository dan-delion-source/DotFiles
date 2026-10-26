"""Load Kanji workspace labels without relying on installed CJK fonts."""
import shutil
import unittest

import test_bar_positions as bars


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class WorkspaceKanjiTests(unittest.TestCase):
    def test_bundled_font_loads_in_both_orientations_and_preview(self):
        owner = bars.BarPositionTests()
        f = owner.rail_fixture()
        self.addCleanup(owner.doCleanups)
        f.shell('inspect.start();', '''
        Window { visible: true; width: 500; height: 500
            WorkspacesWidget { id: horizontal; preview: true; style: "kanji" }
            WorkspacesWidget { id: vertical; x: 300; vertical: true; style: "kanji" }
        }
        Timer { id: inspect; interval: 80; onTriggered: {
            try {
                for (const strip of [horizontal, vertical]) {
                    require(strip.kanjiFontReady, "bundled font loads");
                    require(strip.labelFamily === "DanShell Workspace Kanji", "explicit Kanji family");
                    const expected = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
                    for (let i = 1; i <= 10; i++) require(strip.glyphOf(i) === expected[i-1], "numeral mapping");
                    require(strip.glyphOf(21) === "二十一", "compound numeral");
                    require(strip.glyphOf(100) === "100", "larger workspace fallback");
                    const label = findNamed(strip, "workspaceLabel1");
                    require(label.text === "一" && label.font.family === strip.labelFamily, "label uses bundled face");
                    require(label.contentWidth > 0 && label.contentHeight > 0, "glyph has layout dimensions");
                }
                horizontal.style = "numbers";
                require(horizontal.labelFamily !== "DanShell Workspace Kanji", "other styles keep interface font");
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar/widgets"\n')
