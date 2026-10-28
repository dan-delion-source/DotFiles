pragma Singleton
import QtQuick
QtObject {
    readonly property string name: LockService.user === SettingsService.user
        ? (SettingsService.appearance.name ?? SettingsService.user) : LockService.user
    readonly property string avatar: LockService.user === SettingsService.user
        ? (SettingsService.appearance.avatar ?? "") : ""
    readonly property string initials: name.trim().split(/\s+/).filter(word => word !== "")
        .slice(0, 2).map(word => word[0]).join("").toUpperCase()
}
