// Shared bar and control-centre preferences, extracted from WidgetsSection.
// Original configuration: Andreu Massanet, GPL-3.0; see NOTICE and LICENSE.
import QtQuick
import QtQuick.Layouts
import "../theme"
import "../services"
import "../components"

SettingsSection {
    ColumnLayout {
        Layout.fillWidth: true
        SettingGroup {
            title: Tr.t("Weather")
            note: Tr.t("A city, a postcode or an airport code.")
            hint: Tr.t("Left empty, wttr.in guesses from your connection's IP address, which can be far off. A city, postcode or airport code is more reliable, and the bar uses the same place.")

            // wttr.in answers an unknown place with prose and the module
            // keeps its last reading, so the error is shown here.
            SettingField {
                label: Tr.t("Location")
                reading: WeatherService.placeUnknown
                    ? Tr.t("No such place — the last reading is still showing") : ""
                alarm: WeatherService.placeUnknown
                placeholder: Tr.t("Wherever the request comes from")
                value: SettingsService.weatherPlace
                onEdited: value => SettingsService.set("weatherPlace", value.trim())
            }
        }

        SettingGroup {
            title: "GitHub"
            note: Tr.t("Whose public contribution graph to draw.")
            hint: Tr.t("The graph is read from the public profile page, so no token or account is needed. It stays empty until you enter a username.")

            // An unknown user returns a page with no calendar and the module
            // keeps its last grid, so the error is shown here.
            SettingField {
                label: Tr.t("Username")
                reading: GithubService.userUnknown
                    ? Tr.t("No such profile — the last grid is still showing") : ""
                alarm: GithubService.userUnknown
                placeholder: Tr.t("Nobody yet")
                value: SettingsService.githubUser
                onEdited: value => SettingsService.set(
                    "githubUser", value.trim().replace(/^@/, ""))
            }
        }

        // The tiles draw the pet itself, one in each style, and blink while
        // the pointer is on them.
        SettingGroup {
            title: Tr.t("Pet")
            note: Tr.t("How the creature is drawn, wherever it is drawn.")
            hint: Tr.t("The species decides the colour and what the creature is; the style decides how it is drawn. The same drawing is used on the bar and in the pet's panel.")

            SettingTiles {
                label: Tr.t("Style")
                reading: Tr.t((PetService.styles.find(
                    entry => entry.id === SettingsService.petStyle) ?? { note: "" }).note)

                Repeater {
                    model: PetService.styles

                    PreviewTile {
                        id: petTile

                        required property var modelData

                        stageHeight: 78
                        caption: Tr.t(petTile.modelData.label)
                        selected: SettingsService.petStyle === petTile.modelData.id
                        onPicked: SettingsService.set("petStyle", petTile.modelData.id)

                        // An egg is an egg in three of the four styles, so
                        // the tiles draw the creature inside it.
                        PetFace {
                            anchors.centerIn: parent
                            size: 58
                            style: petTile.modelData.id
                            record: Object.assign({}, PetService.pet, { hatchedAt: 1 })
                            lively: petTile.hovered
                        }
                    }
                }
            }
        }

        SettingGroup {
            title: Tr.t("Notes")
            note: Tr.t("How note text is drawn in the notes panel.")
            hint: Tr.t("Choose handwriting or the interface font for note bodies.")

            SettingRow {
                label: Tr.t("Handwriting")
                reading: SettingsService.notesHandwriting
                    ? Tr.t("The signature's script") : Tr.t("The interface face")

                ToggleSwitch {
                    checked: SettingsService.notesHandwriting
                    onToggled: checked => SettingsService.set("notesHandwriting", checked)
                }
            }

        }

    }
}
