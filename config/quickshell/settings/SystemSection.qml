// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S Y S T E M   S E C T I O N                                            │
// │   system · profiles, machine info and reset                              │
// │                                                                          │
// │   github.com/andreumassanet/impasto                                      │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import QtQuick.Layouts
import Quickshell

import "../theme"
import "../services"
import "../components"

// Two parts: the profiles, with Reset under them (it resets only the active
// profile), and this machine: language, hardware and the colophon.
SettingsSection {
    id: root

    property string tab: "profiles"

    function spell(seconds: int): string {
        const days = Math.floor(seconds / 86400)
        const hours = Math.floor((seconds % 86400) / 3600)
        const minutes = Math.floor((seconds % 3600) / 60)
        if (days > 0)
            return `${days}d ${hours}h`
        if (hours > 0)
            return `${hours}h ${minutes}m`
        return `${minutes}m`
    }

    // ── PROFILES ────────────────────────────────────────────────────────────

    ColumnLayout {
        Layout.fillWidth: true
        visible: root.tab === "profiles"
        spacing: root.spacing

        ProfilesPart {}

        SettingGroup {
            title: Tr.t("Library updates")
            note: Tr.t("Refresh the logos available in Appearance → Greeting.")
            hint: Tr.t("Add TXT, PNG, JPG, WebP or GIF files to your Fastfetch logos folder, then click Update Greeter. Wallpapers refresh automatically from ~/Pictures/Wallpapers and its animated subfolder.")

            SettingRow {
                label: Tr.t("Greeter")
                reading: ThemeService.refreshingGreetings ? Tr.t("Scanning…")
                    : ThemeService.greetingScanError || ThemeService.greetingScanStatus
                        || Tr.t("Scan the Fastfetch logos folder")
                alarm: ThemeService.greetingScanError !== ""

                PillButton {
                    text: Tr.t("Update Greeter")
                    icon: "󰜉"
                    implicitHeight: 30
                    enabled: !ThemeService.refreshingGreetings
                    onClicked: ThemeService.refreshGreetings()
                }
            }
        }

        SettingGroup {
            title: Tr.t("Reset")
            note: Tr.t("Only the profile in use. The others are left as they were.")
            hint: Tr.t("Reset returns every setting in this profile to its default, clears the compositor overrides and reloads Hyprland. Machine settings such as screens, name, picture and language are kept, and there is no undo.")

            SettingRow {
                label: Tr.t("Where the settings live")

                Text {
                    text: SettingsService.stateDirectory
                    font.family: Theme.fontMono
                    font.pixelSize: Theme.fontSizeLabel
                    color: Theme.textMuted
                }
            }

            SettingRow {
                label: Tr.t("Reset this profile")
                reading: Tr.t("Back to the defaults")

                PillButton {
                    text: Tr.t("Reset")
                    icon: "󰜉"
                    implicitWidth: 92
                    implicitHeight: 30
                    onClicked: {
                        SettingsService.reset()
                        CompositorService.restoreDefaults()
                    }
                }
            }
        }
    }

    // ── THIS MACHINE ────────────────────────────────────────────────────────

    ColumnLayout {
        Layout.fillWidth: true
        visible: root.tab === "machine"
        spacing: root.spacing

        // Strings missing from `Tr.qml` fall back to English.
        SettingGroup {
            title: Tr.t("This window")
            note: Tr.t("The language of this window.")
            hint: Tr.t("Only the settings window is translated, and anything without a translation appears in English. Files the shell writes, such as generated themes, are always in English.")

            SettingRow {
                label: Tr.t("Language")

                SegmentedControl {
                    options: Tr.languages
                    current: SettingsService.language
                    onSelected: id => SettingsService.set("language", id)
                }
            }
        }

        SettingGroup {
            title: Tr.t("This machine")

            SettingBlock {
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    Figure {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        label: Tr.t("PROCESSOR")
                        value: StatsService.cpuModel || "—"
                        note: `${StatsService.cores.length} ${Tr.t("threads")}`
                    }

                    Figure {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        label: Tr.t("MEMORY")
                        value: StatsService.memoryTotal > 0
                            ? `${(StatsService.memoryTotal / 1024 / 1024 / 1024).toFixed(1)} GiB`
                            : "—"
                        note: `${Math.round(StatsService.memoryFraction * 100)}${Tr.t("% in use")}`
                    }

                    Figure {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        label: Tr.t("UPTIME")
                        value: StatsService.uptime > 0 ? root.spell(StatsService.uptime) : "—"
                        note: Tr.t("since boot")
                    }

                }
            }
        }


    }
}
