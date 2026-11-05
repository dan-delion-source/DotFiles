// ╭──────────────────────────────────────────────────────────────────────────╮
// │                                                                          │
// │   S E T T I N G S   P A N E L                                            │
// │   flat navigation, fixed header, and scrollable settings pages        │
// │                                                                          │
// │                                                                          │
// ╰──────────────────────────────────────────────────────────────────────────╯

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC

import "../theme"
import "../services"
import "../components"

// Navigation and page. `SettingsWindow` owns the window; this owns the sections.
//
// Settings are filed by what they change, not by how they are applied. The
// sidebar index selects a page, and SettingsTabs keeps its existing parts
// visible above the scrollable controls.
//
// Where an option is a shape, the control is a live miniature built from the
// real components (`PreviewTile`), so it follows the palette and cannot go
// stale the way a screenshot would.
Item {
    id: root

    objectName: "settingsPanel"
    readonly property bool settingsPresentation: true

    signal closed()
    signal panelRequested(string panel)

    readonly property int gap: 12
    property bool ready: false
    Component.onCompleted: { commitPage(); ready = true }
    property var displayedPage: current.page
    property string displayedTab: tab
    function switchPage() {
        if (!root.ready) return
        pageEnter.stop()
        if (Theme.motion === 0) { pageExit.stop(); commitPage(); body.opacity = 1; body.scale = 1; body.y = 0; return }
        pageExit.restart()
    }
    function commitPage() {
        displayedPage = current.page
        displayedTab = tab
        page.contentY = 0
    }
    onSectionChanged: switchPage()
    onTabChanged: switchPage()
    SequentialAnimation {
        id: pageExit
        NumberAnimation { target: body; property: "opacity"; to: 0; duration: 90 * Theme.motion; easing.type: Easing.InCubic }
        ScriptAction { script: { root.commitPage(); pageEnter.restart() } }
    }
    ParallelAnimation {
        id: pageEnter
        NumberAnimation { target: body; property: "opacity"; from: 0; to: 1; duration: 260 * Theme.motion; easing.type: Easing.BezierSpline; easing.bezierCurve: [0.05, 0.7, 0.1, 1, 1, 1] }
        NumberAnimation { target: body; property: "scale"; from: 0.95; to: 1; duration: 420 * Theme.motion; easing.type: Easing.BezierSpline; easing.bezierCurve: [0.05, 0.7, 0.1, 1, 1, 1] }
        NumberAnimation { target: body; property: "y"; from: 18; to: 0; duration: 420 * Theme.motion; easing.type: Easing.OutCubic }
    }
    Rectangle { anchors.fill: parent; color: Theme.background }
    NumberAnimation on opacity { from: 0; to: 1; duration: 320 * Theme.motion; easing.type: Easing.OutCubic }
    NumberAnimation on scale { from: 0.975; to: 1; duration: 480 * Theme.motion; easing.type: Easing.OutCubic }


    // ── THE GROUPS ──────────────────────────────────────────────────────────

    readonly property var categories: [
        { id: "shell",   label: Tr.t("Shell") },
        { id: "desk",    label: Tr.t("Desktop") },
        { id: "session", label: Tr.t("Session") }
    ]

    // ── THE SECTIONS ────────────────────────────────────────────────────────
    //
    // One row per page. `keywords` are extra search terms beyond the label.
    readonly property var sections: [
        { id: "bar", category: "shell", icon: "󰧨", label: Tr.t("Bar & Island"),
          blurb: Tr.t("The top bar, the island and notifications."),
          tabs: [{ id: "island", label: Tr.t("The island") },
                 { id: "modules", label: Tr.t("The bar") },
                 { id: "preferences", label: Tr.t("Module settings") },
                 { id: "workspaces", label: Tr.t("Workspaces") },
                 { id: "notifications", label: Tr.t("Notifications") }],
          keywords: "bar position edge top bottom left right vertical horizontal island notch height margin width full span workspaces unified layout island bar band notification toast do not disturb silence timeout clock time date seconds format beside running modules layout left right split drag catalogue running cat animation weather location city github username pet style notes handwriting chip icon ring figure hover shape media claude battery timer volume brightness network wifi bluetooth weather stats cpu updates pet capture record screenshot buttons every screen monitors ground glass classic blur transparent translucent codex",
          page: barPage },

        { id: "controls", category: "shell", icon: "󰕰", label: Tr.t("Control Centre"),
          blurb: Tr.t("What the island opens onto when you click it."),
          tabs: [],
          keywords: "controls control centre center panel doors buttons row network speed upload download system info pet games notes board tasks kanban stats blocks grid toggles tiles arrange edit tray wifi bluetooth airplane microphone focus",
          page: controlsPage },


        { id: "launcher", category: "shell", icon: "󰍉", label: Tr.t("Launcher"),
          blurb: Tr.t("Search, sigils and the clipboard history."),
          tabs: [{ id: "results", label: Tr.t("Results") },
                 { id: "sigils", label: Tr.t("Sigils") },
                 { id: "clipboard", label: Tr.t("Clipboard") }],
          keywords: "launcher search apps results calculate run window timer note task board prefix sigil order recent frequency favourite favorite pinned kept clipboard history copy paste images wipe lock",
          page: launcherPage },

        { id: "appearance", category: "desk", icon: "󰏘", label: Tr.t("Appearance"),
          blurb: Tr.t("Palette, windows, fonts and animations."),
          tabs: [{ id: "theme", label: Tr.t("Theme") },
                 { id: "windows", label: Tr.t("Windows") },
                 { id: "depth", label: Tr.t("Depth") },
                 { id: "type", label: Tr.t("Type") },
                 { id: "motion", label: Tr.t("Motion") }],
          keywords: "appearance theme colour color wallpaper transition fade wipe wave circle random greeting fastfetch fa terminal arch cat gif logo shadow shadows depth ground glass classic rounding blur gaps border opacity glass rules font family sans mono nerd icons typeface animation speed curve easing preset motion",
          page: appearancePage },

        { id: "monitors", category: "desk", icon: "󰍹", label: Tr.t("Displays"),
          blurb: Tr.t("Screen layout, modes and the laptop lid."),
          tabs: [{ id: "arrangement", label: Tr.t("Arrangement") },
                 { id: "screen", label: Tr.t("The screen") },
                 { id: "lid", label: Tr.t("The lid") }],
          keywords: "displays monitor screen resolution refresh scale rotate transform vrr mirror extend primary lid clamshell laptop close workspaces",
          page: monitorsPage },

        { id: "input", category: "desk", icon: "󰍽", label: Tr.t("Input"),
          blurb: Tr.t("The keyboard, the pointer and the cursor."),
          tabs: [{ id: "keyboard", label: Tr.t("Keyboard") },
                 { id: "pointer", label: Tr.t("Pointer") }],
          keywords: "input keyboard layout repeat mouse sensitivity pointer cursor size theme shake find",
          page: inputPage },

        { id: "keys", category: "desk", icon: "󰌌", label: Tr.t("Keys"),
          blurb: Tr.t("Every keybinding, the shell's and Hyprland's."),
          tabs: [{ id: "shell", label: Tr.t("The shell's own") },
                 { id: "compositor", label: Tr.t("The compositor's") }],
          keywords: "keys shortcut binding hotkey super rebind",
          page: keysPage },

        { id: "session", category: "session", icon: "󰌾", label: Tr.t("Session"),
          blurb: Tr.t("Your account, the lock screen and idle behaviour."),
          tabs: [{ id: "lock", label: Tr.t("Lock screen") },
                 { id: "idle", label: Tr.t("When you leave") }],
          keywords: "session lock style classic mainframe crt terminal blur password suspend security idle timeout sleep screen off dpms away never lock after avatar picture name account clock stacked inline face unlock howdy camera infrared enrol enroll scan faces recognise",
          page: sessionPage },

        { id: "system", category: "session", icon: "󰍛", label: Tr.t("System"),
          blurb: Tr.t("Profiles, language, this machine and reset."),
          tabs: [{ id: "profiles", label: Tr.t("Profiles") },
                 { id: "machine", label: Tr.t("This machine") }],
          keywords: "system about cpu memory uptime reset defaults language spanish english profile profiles switch rename duplicate delete import export backup json wallpapers config library update greeter greeting fastfetch logos refresh scan",
          page: systemPage }
    ]

    // ── NAVIGATION ──────────────────────────────────────────────────────────
    //
    // A history rather than a single id, so a page that links to another can
    // be left with the back button.
    property var trail: [{ section: "bar", tab: "island" }]
    property int cursor: 0

    readonly property string section: root.trail[root.cursor].section
    readonly property string tab: root.trail[root.cursor].tab

    readonly property var current:
        root.sections.find(entry => entry.id === root.section) ?? root.sections[0]

    function firstTab(id: string): string {
        const entry = root.sections.find(other => other.id === id)
        return entry && entry.tabs.length > 0 ? entry.tabs[0].id : ""
    }

    // The part each section was last left on.
    property var visited: ({})

    function go(id: string, wanted: string): void {
        const part = wanted !== undefined && wanted !== ""
            ? wanted : (root.visited[id] ?? root.firstTab(id))
        if (id === root.section && part === root.tab)
            return
        const path = root.trail.slice(0, root.cursor + 1)
        path.push({ section: id, tab: part })
        root.trail = path
        root.cursor = path.length - 1
        page.contentY = 0
    }

    function show(part: string): void {
        if (part === root.tab)
            return
        const kept = Object.assign({}, root.visited)
        kept[root.section] = part
        root.visited = kept
        const path = root.trail.slice()
        path[root.cursor] = { section: root.section, tab: part }
        root.trail = path
        page.contentY = 0
    }

    function back(): void {
        if (root.cursor > 0) {
            root.cursor--
            page.contentY = 0
        }
    }

    function forward(): void {
        if (root.cursor < root.trail.length - 1) {
            root.cursor++
            page.contentY = 0
        }
    }

    property string filter: ""

    function matches(entry: var): bool {
        const term = root.filter.trim().toLowerCase()
        if (term === "")
            return true
        // Labels are translated; keywords are English, so both languages match.
        const parts = entry.tabs.map(part => part.label).join(" ").toLowerCase()
        return entry.label.toLowerCase().includes(term)
            || entry.keywords.includes(term)
            || entry.blurb.toLowerCase().includes(term)
            || parts.includes(term)
    }

    readonly property var shown: root.sections.filter(entry => root.matches(entry))

    readonly property var navigation: root.shown

    onShownChanged: {
        if (root.filter.trim() !== "" && root.shown.length > 0
                && !root.shown.some(entry => entry.id === root.section))
            root.go(root.shown[0].id, "")
    }

    Shortcut {
        sequence: "Ctrl+F"
        onActivated: { search.forceActiveFocus(); search.selectAll() }
    }

    Keys.onEscapePressed: {
        if (root.filter !== "") search.clear()
        else root.closed()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.preferredWidth: 96
            Layout.fillHeight: true
            color: Theme.surface
            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 14
                anchors.bottomMargin: 12
                spacing: 10
                QQC.AbstractButton {
                    id: profile
                    Layout.alignment: Qt.AlignHCenter
                    implicitWidth: 48; implicitHeight: 48
                    focusPolicy: Qt.StrongFocus
                    Accessible.name: AccountService.name + " · " + Tr.t("Session")
                    QQC.ToolTip.visible: hovered
                    QQC.ToolTip.text: AccountService.name
                    onClicked: root.go("session", "lock")
                    scale: down ? 0.94 : hovered ? 1.05 : 1
                    Behavior on scale { NumberAnimation { duration: 220 * Theme.motion; easing.type: Easing.OutBack } }
                    background: Rectangle {
                        radius: width / 2
                        gradient: Gradient {
                            GradientStop { position: 0; color: Theme.accent }
                            GradientStop { position: 1; color: Theme.textMuted }
                        }
                        rotation: profile.hovered ? 180 : 0
                        Behavior on rotation { NumberAnimation { duration: 700 * Theme.motion; easing.type: Easing.OutCubic } }
                        border.width: profile.visualFocus ? 2 : 0
                        border.color: Theme.text
                    }
                    contentItem: Item {
                        Avatar { anchors.fill: parent; source: AccountService.avatar; initials: AccountService.avatar === "" ? "" : AccountService.initials }
                        Text {
                            anchors.centerIn: parent
                            visible: AccountService.avatar === ""
                            text: AccountService.initials
                            font.family: Theme.fontFamily
                            font.pixelSize: 18
                            color: Theme.text
                        }
                    }
                    padding: 3
                }
                ListView {
                    id: navigationList
                    objectName: "settingsNavigation"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 4
                    model: root.navigation
                    boundsBehavior: Flickable.StopAtBounds
                    currentIndex: root.navigation.findIndex(entry => entry.id === root.section)
                    QQC.ScrollBar.vertical: QQC.ScrollBar { width: 3 }
                    delegate: QQC.AbstractButton {
                        id: navEntry
                        required property var modelData
                        readonly property bool selected: root.section === modelData.id
                        width: navigationList.width
                        height: 60
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: modelData.label
                        QQC.ToolTip.visible: hovered
                        QQC.ToolTip.text: modelData.label
                        onClicked: root.go(modelData.id, "")
                        background: Item {
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: 3; height: 32
                                width: navEntry.selected || navEntry.hovered ? 58 : 28
                                radius: 16
                                color: navEntry.selected ? Qt.rgba(Theme.accent.r, Theme.accent.g, Theme.accent.b, 0.18) : Theme.surfaceHover
                                opacity: navEntry.selected || navEntry.hovered ? 1 : 0
                                border.width: navEntry.visualFocus ? 1 : 0
                                border.color: Theme.accent
                                Behavior on width { NumberAnimation { duration: 320 * Theme.motion; easing.type: Easing.OutCubic } }
                                Behavior on opacity { NumberAnimation { duration: 160 * Theme.motion } }
                            }
                        }
                        contentItem: Item {
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: 7
                                text: navEntry.modelData.icon
                                font.family: Theme.fontMono
                                font.pixelSize: 17
                                color: navEntry.selected ? Theme.accent : Theme.textMuted
                                Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                            }
                            Text {
                                y: 36; width: parent.width - 8; x: 4
                                text: navEntry.modelData.label
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.Wrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.weight: navEntry.selected ? Font.DemiBold : Font.Medium
                                color: navEntry.selected ? Theme.text : Theme.textMuted
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        width: parent.width - 12
                        visible: root.shown.length === 0
                        text: Tr.t("No matching settings")
                        wrapMode: Text.Wrap
                        horizontalAlignment: Text.AlignHCenter
                        font.family: Theme.fontFamily
                        font.pixelSize: 11
                        color: Theme.textMuted
                    }
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 20
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Text {
                        Layout.fillWidth: true
                        text: root.current.label
                        font.family: Theme.fontFamily
                        font.pixelSize: 26
                        font.weight: Font.Medium
                        color: Theme.text
                        elide: Text.ElideRight
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.current.blurb
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        color: Theme.textMuted
                        elide: Text.ElideRight
                    }
                }
                QQC.TextField {
                    id: search
                    objectName: "settingsSearch"
                    Layout.preferredWidth: root.width < 850 ? 150 : 190
                    Layout.preferredHeight: 36
                    placeholderText: Tr.t("Search settings")
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fontSizeSmall
                    color: Theme.text
                    placeholderTextColor: Theme.textMuted
                    selectionColor: Theme.accent
                    selectedTextColor: Theme.accentText
                    leftPadding: 16; rightPadding: 12
                    selectByMouse: true
                    focus: true
                    onTextChanged: root.filter = text
                    Accessible.name: Tr.t("Search settings")
                    background: Rectangle {
                        radius: 20
                        color: Theme.surface
                        border.width: search.activeFocus ? 1 : 0
                        border.color: Theme.accent
                    }
                    Keys.onReturnPressed: { if (root.shown.length > 0) root.go(root.shown[0].id, "") }
                    Keys.onEscapePressed: { if (search.text !== "") search.clear(); else root.closed() }
                }
                Repeater {
                    model: [
                        { id: "back", glyph: "󰅁", hint: Tr.t("Back"), available: root.cursor > 0 },
                        { id: "forward", glyph: "󰅂", hint: Tr.t("Forward"), available: root.cursor < root.trail.length - 1 },
                        { id: "close", glyph: "󰅖", hint: Tr.t("Close"), available: true }
                    ]
                    delegate: QQC.AbstractButton {
                        id: action
                        required property var modelData
                        implicitWidth: 28; implicitHeight: 28
                        enabled: modelData.available
                        focusPolicy: Qt.StrongFocus
                        Accessible.name: modelData.hint
                        QQC.ToolTip.visible: hovered
                        QQC.ToolTip.text: modelData.hint
                        onClicked: {
                            if (modelData.id === "back") root.back()
                            else if (modelData.id === "forward") root.forward()
                            else root.closed()
                        }
                        background: Rectangle {
                            radius: 16
                            color: action.hovered ? Theme.surfaceHover : Theme.surface
                            border.width: action.visualFocus ? 1 : 0
                            border.color: Theme.accent
                            Behavior on color { ColorAnimation { duration: Theme.durationFast } }
                        }
                        contentItem: Text {
                            text: action.modelData.glyph
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.family: Theme.fontMono
                            font.pixelSize: 15
                            color: Theme.text
                            opacity: action.enabled ? 1 : 0.35
                        }
                    }
                }
            }
            SettingsTabs {
                Layout.fillWidth: true
                tabs: root.current.tabs
                current: root.tab
                onPicked: id => root.show(id)
            }
            Flickable {
                id: page
                objectName: "settingsContent"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: width
                contentHeight: body.implicitHeight + 16
                boundsBehavior: Flickable.StopAtBounds
                QQC.ScrollBar.vertical: QQC.ScrollBar { policy: QQC.ScrollBar.AsNeeded; width: 8; interactive: true }
                ColumnLayout {
                    id: body
                    enabled: !pageExit.running && !pageEnter.running
                    transformOrigin: Item.Top
                    width: Math.max(0, page.width - 16)
                    spacing: root.gap
                    Loader {
                        id: pageLoader
                        objectName: "settingsPageLoader"
                        Layout.fillWidth: true
                        sourceComponent: root.displayedPage
                        onLoaded: pageLoader.item.tab = Qt.binding(() => root.displayedTab)
                    }
                }
            }
        }
    }

    Component { id: barPage;        BarSection {} }
    // Open the control centre before closing, while this panel still exists
    // to emit the request.
    Component { id: controlsPage;   ControlsSection {
        onArranging: {
            root.panelRequested("controls")
            root.closed()
        } } }
    Component { id: launcherPage;   LauncherSection {} }
    Component { id: appearancePage; AppearanceSection {
        onPanelRequested: name => root.panelRequested(name) } }
    Component { id: inputPage;      InputSection {} }
    Component { id: monitorsPage;   MonitorsSection {} }
    Component { id: keysPage;       KeysSection {} }
    Component { id: sessionPage;    SessionSection {} }
    Component { id: systemPage;     SystemSection {} }
}
