"""Old desktop placements must not interfere with bar state or notes."""
import json
import shutil
import unittest

import test_lock_styles as integration


@unittest.skipUnless(shutil.which("qs"), "QuickShell is required")
class DesktopRemovalTests(unittest.TestCase):
    def test_legacy_settings_and_notes_work_without_desktop_services(self):
        fixture = integration.LockStyleIntegrationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        shutil.copy2(integration.ROOT / "services/NotesService.qml",
                     fixture.root / "services/NotesService.qml")
        (fixture.root / "state/danshell/settings.json").write_text(json.dumps({
            "barLeft": ["clock", "runningCat"], "barRight": ["volume"],
            "weatherPlace": "Bengaluru", "petStyle": "pixel",
            "desktopWidgets": [{"id": "notes", "key": "notes-1"}],
            "desktopHidden": False, "desktopTheme": "analogue",
            "desktopGround": "glass", "widgetShadow": True,
        }))
        (fixture.root / "state/danshell/notes.json").write_text(json.dumps({
            "notes": [{"key": "kept", "title": "Keep this", "text": "My note"}]
        }))
        # First access loads NotesService; give its FileView time to arrive.
        fixture.shell('''
            require(SettingsService.barZone("left")[1] === "runningCat", "bar preserved");
            require(SettingsService.weatherPlace === "Bengaluru", "shared preference preserved");
            require(SettingsService.petStyle === "pixel", "pet style preserved");
            require(!("desktopWidgets" in SettingsService.snapshot()), "obsolete fields excluded");
            const oldProfile = { desktopWidgets: [{id: "clock"}], desktopHidden: false,
                barLeft: ["runningCat", "clock"], petStyle: "plush" };
            SettingsService.adopt(oldProfile);
            require(SettingsService.barZone("left")[0] === "runningCat", "old profile bar works");
            require(NotesService.entry("kept").text === "My note", "existing notes preserved");
            const key = NotesService.add("New note", "Still works");
            NotesService.archive(key);
            require(NotesService.entry(key).archived, "archive works");
            NotesService.archive(key, false);
            require(!NotesService.entry(key).archived, "restore works");
            NotesService.remove(key);
            require(NotesService.entry(key) === null, "remove works");
            require(NotesService.entry("kept").text === "My note", "unrelated note retained");
            finish.start();
        ''', '''Component.onCompleted: { const count = NotesService.count; }''')
