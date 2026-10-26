"""Vertical picker layouts and actions with fake wallpaper/theme services."""
import shutil
import unittest

import test_bar_positions as bars
import test_lock_styles as integration


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class SidePickerTests(unittest.TestCase):
    def fixture(self):
        owner = bars.BarPositionTests()
        f = owner.rail_fixture()
        self.addCleanup(owner.doCleanups)
        shutil.copy2(integration.ROOT / "services/GamesService.qml", f.root / "services/GamesService.qml")
        colors = '({accent: "#89b4fa", green: "#a6e3a1", yellow: "#f9e2af", red: "#f38ba8", blue: "#89b4fa"})'
        (f.root / "services/ThemeService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property string error: ""
    property string activeId: "one"
    property var dynamicColors: ''' + colors + '''
    property var availableThemes: [
        {id: "one", name: "First", badge: "Preset", adaptive: true},
        {id: "two", name: "Second", badge: "Preset", adaptive: true}]
    function setTheme(id) { activeId = id }
}''')
        (f.root / "services/WallpaperService.qml").write_text('''pragma Singleton
import QtQuick
import Quickshell
Singleton {
    property string chosen: Qt.resolvedUrl("../assets/running-cat/cat_f0.png").toString().replace("file://", "")
    property bool scanning: false
    property var wallpapers: [0,1,2,3].map(n => ({name: "Wallpaper " + n,
        path: Qt.resolvedUrl("../assets/running-cat/cat_f" + n + ".png").toString().replace("file://", "")}))
    property var animated: []
    function scan() {}
    function apply(path) { chosen = path }
}''')
        return f

    def test_vertical_browsing_actions_and_game_board_scale(self):
        f = self.fixture()
        f.shell('''
            SettingsService.set("barPosition", "left");
            SettingsService.set("motionScale", 0);
            inspect.start();
        ''', '''
        Window { visible: true; width: 760; height: 640
            AppearancePanel { id: appearance; x: 20; y: 20; width: 320; height: 580 }
            GamesPanel { id: games; x: 400; y: 20; width: 320; height: 580 }
        }
        Timer { id: inspect; interval: 150; onTriggered: {
            try {
                const wallpaper = findNamed(appearance, "wallpaperCarousel");
                const palette = findNamed(appearance, "paletteCarousel");
                const shelf = findNamed(games, "gameCarousel");
                for (const strip of [wallpaper, palette, shelf]) {
                    require(strip.vertical, "side picker is vertical");
                    require(strip.width > 0 && strip.height > strip.width, "portrait picker viewport");
                    const tiles = strip.children.filter(child => child.index !== undefined);
                    require(tiles.length >= 2, "populated picker");
                    require(Math.abs(tiles[0].x - tiles[1].x) < 1 && tiles[0].y !== tiles[1].y, "cards stack upright");
                }
                wallpaper.step(1);
                appearance.apply();
                require(WallpaperService.chosen === WallpaperService.wallpapers[1].path, "wallpaper action retained");
                appearance.shown = "palette";
                palette.goTo(1);
                appearance.apply();
                require(ThemeService.activeId === "two", "palette action retained");
                SettingsService.set("barPosition", "right");
                require(wallpaper.vertical && shelf.vertical, "right edge is vertical too");
                SettingsService.set("barPosition", "top");
                require(!wallpaper.vertical && !shelf.vertical, "top retains horizontal layout");
                SettingsService.set("barPosition", "left");
                GamesService.open("whack");
                played.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        Timer { id: played; interval: 80; onTriggered: {
            try {
                const board = findNamed(games, "activeGameBoard");
                require(board && board.scale < 1 && board.scale > 0, "native board fits portrait frame");
                require(board.width === GamesService.entry("whack").width, "game aspect preserved");
                GamesService.leave();
                finish.start();
            } catch (error) { console.error("LOCK_TEST_FAILED", error); Qt.quit(); }
        } }
        ''', imports='import QtQuick.Window\nimport "./bar/island"\n')
