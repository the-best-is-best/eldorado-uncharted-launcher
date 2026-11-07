// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The Settings screen: the game being edited (Uncharted 1/2/3), the tabs, and the chosen tab's rows from the
// `settings` model. Keys (from Main.qml): Up/Down move, Enter changes or runs the row (a choice steps to its next
// value), Left/Right switch tabs. Row -1 is the game switch. Buttons call the `app` object when it is there.
import QtQuick
import QtQuick.Controls
import QtQuick.Window
import ".."
import "../components"

Page {
    id: page
    title: qsTr("SETTINGS")
    // The Controls tab has its own scope (ALL GAMES or one game) instead of the game being edited.
    subtitle: tabKey === "controls" ? settings.controlsScopeName : (perGame ? settings.gameName : qsTr("All games"))

    property int tab: 0
    property int cursor: 0
    readonly property string tabKey: settings.tabs[tab].key
    readonly property bool setup: tabKey === "setup"
    // Quick setup, Display and Performance show one game (the EDITING switch); the other tabs are for all games.
    readonly property bool perGame: ["setup", "display", "performance"].indexOf(tabKey) >= 0
    readonly property var rows: setup ? [] : (settings.pages[tabKey] || [])
    readonly property int count: setup ? settings.presets.length : rows.length
    property Item focusBefore: null

    // --- keys -----------------------------------------------------------------------------------------------------

    function selectable(index) {
        if (index === -1) return perGame   // the game switch is shown only on the per-game tabs
        if (setup) return index >= 0 && index < count
        var row = rows[index]
        return row !== undefined && row.kind !== "note" && row.kind !== "section" && row.enabled !== false
    }
    function step(direction) {
        var index = cursor + direction
        while (index >= -1 && index < count && !selectable(index)) index += direction
        if (index >= -1 && index < count) cursor = index
        Qt.callLater(reveal)
    }
    function up() { step(-1) }
    function down() { step(1) }
    function showTab(index) { tab = index }
    // However the tab changes (keys, a click, the controller), the keys start on its first row they can act on.
    onTabChanged: { cursor = 0; flick.contentY = 0; Qt.callLater(settle) }
    // The rows arrive after the tab (and change with the language): the keys move off a title or a note.
    onRowsChanged: Qt.callLater(settle)
    function settle() { if (cursor >= 0 && !selectable(cursor)) step(1) }
    function moveLeft() { showTab((tab + settings.tabs.length - 1) % settings.tabs.length) }
    function moveRight() { showTab((tab + 1) % settings.tabs.length) }
    function accept() {
        if (cursor === -1) { settings.selectGame((settings.gameIndex + 1) % settings.games.length); return }
        if (setup) { settings.applyPreset(settings.presets[cursor].name); return }
        var row = rows[cursor]
        if (!row || row.enabled === false) return
        if (row.kind === "toggle") settings.set(row.key, !row.checked)
        else if (row.kind === "choice") settings.set(row.key, nextValue(row))
        else if (row.kind === "button") run(row.action, row.arg)
        else if (row.kind === "binding") startCapture(row.action, 0)
    }
    function nextValue(row) {
        for (var i = 0; i < row.options.length; i++)
            if (row.options[i].value === row.value) return row.options[(i + 1) % row.options.length].value
        return row.options[0].value
    }
    function reveal() {
        var item = cursor < 0 ? null : (setup ? cards.itemAt(cursor) : lines.itemAt(cursor))
        if (!item) { flick.contentY = 0; return }
        // The first row the keys can reach shows the whole top of the tab with it (the notes above it, such as
        // the game's version on GAME FILES); any other row keeps a little room above it.
        var first = true
        for (var i = 0; i < cursor; i++) if (selectable(i)) { first = false; break }
        if (first) { flick.contentY = 0; return }
        var top = item.mapToItem(flick.contentItem, 0, 0).y - 12
        if (top < flick.contentY) flick.contentY = Math.max(0, top)
        else if (top + item.height + 24 > flick.contentY + flick.height)
            flick.contentY = Math.min(top + item.height + 24 - flick.height, Math.max(0, flick.contentHeight - flick.height))
    }

    // --- actions ----------------------------------------------------------------------------------------------------

    function run(action, argument) {
        if (action === "resetControls") { settings.resetControls(); return }
        if (action === "useAllGamesKeys") { settings.dropOwn(); return }
        if (typeof app === "undefined") return
        if (action === "openFolder") app.openFolder(argument)
        else if (action === "chooseGameFolder") app.chooseGameFolder()
        else if (action === "installUpdatePkg") app.installUpdatePkg()
        else if (action === "installGamePkg") app.installGamePkg()
        else if (action === "checkGameFiles") app.checkGameFiles()
        else if (action === "clearShaderCache") app.clearShaderCache()
        else if (action === "createShortcuts") app.createShortcuts()
        else if (action === "addToSteam") app.addToSteam(argument === "games")
        else if (action === "checkForUpdates") app.checkForUpdates()
        else if (action === "resetSettings") app.resetSettings()
    }
    function startCapture(action, slot) {
        focusBefore = Window.activeFocusItem
        settings.startCapture(action, slot)
        catcher.forceActiveFocus()
        arming.restart()
    }

    Connections {
        target: settings
        function onChanged() {
            if (settings.capturing === "" && page.focusBefore) {
                page.focusBefore.forceActiveFocus()
                page.focusBefore = null
            }
            if (page.cursor >= page.count) page.cursor = Math.max(-1, page.count - 1)
        }
    }
    // A game folder or update chosen, a .pkg installed, a reset: the rows (and the Advanced note) read again.
    Connections {
        target: typeof app !== "undefined" ? app : null
        function onFilesChanged() { settings.refresh() }
    }

    // --- the game switch and the tabs ---------------------------------------------------------------------------------

    Column {
        id: head
        width: parent.width
        spacing: 14
        Row {
            spacing: 8
            visible: page.perGame
            Text { text: qsTr("EDITING"); color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 11; font.letterSpacing: Theme.tracking(2); anchors.verticalCenter: parent.verticalCenter }
            Repeater {
                model: settings.games
                Rectangle {
                    readonly property bool chosen: index === settings.gameIndex
                    readonly property color tone: Theme.accentOf(modelData.key)
                    width: gameLabel.implicitWidth + 30; height: 32; radius: height / 2
                    color: chosen ? Qt.rgba(tone.r, tone.g, tone.b, page.cursor === -1 ? 0.24 : 0.16)
                                  : gameArea.containsMouse ? Theme.glassHover : "transparent"
                    border.color: chosen ? (page.cursor === -1 ? tone : Qt.rgba(tone.r, tone.g, tone.b, 0.6))
                                         : (page.cursor === -1 ? Theme.faint : Theme.line)
                    border.width: chosen && page.cursor === -1 ? 2 : 1
                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                    Text { id: gameLabel; anchors.centerIn: parent; text: modelData.short; color: parent.chosen ? Theme.ink : Theme.dim; font.family: parent.chosen ? Theme.strongFont : Theme.bodyFont; font.pixelSize: 12; font.letterSpacing: Theme.tracking(2) }
                    MouseArea { id: gameArea; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: settings.selectGame(index) }
                }
            }
        }
        // The tabs wrap onto a second line in a narrow window (none is cut off).
        Flow {
            width: parent.width
            spacing: 26
            Repeater {
                model: settings.tabs
                Column {
                    spacing: 8
                    Text {
                        text: modelData.title
                        color: index === page.tab || tabArea.containsMouse ? Theme.ink : Theme.faint
                        font.family: index === page.tab ? Theme.strongFont : Theme.bodyFont; font.pixelSize: 13; font.letterSpacing: Theme.tracking(2)
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                        MouseArea { id: tabArea; anchors.fill: parent; anchors.margins: -6; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: page.showTab(index) }
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: index === page.tab ? parent.width : 0; height: 3; radius: 2
                        color: Theme.accent
                        Behavior on width { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
                    }
                }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Theme.line }
    }

    // --- the tab ----------------------------------------------------------------------------------------------------

    Flickable {
        id: flick
        anchors { top: head.bottom; topMargin: 12; left: parent.left; leftMargin: -14; right: parent.right; rightMargin: 20; bottom: hints.top; bottomMargin: 10 }
        contentHeight: body.height + 24
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: flickBar

        Column {
            id: body
            anchors { left: parent.left; leftMargin: 14 }
            width: flick.width - 22
            spacing: 6

            // Quick setup.
            Text { visible: page.setup; width: parent.width; text: settings.setupNote; color: Theme.dim; font.family: Theme.bodyFont; font.pixelSize: 13; wrapMode: Text.WordWrap; lineHeight: 1.3 }
            Grid {
                visible: page.setup
                columns: 3
                spacing: 14
                Repeater {
                    id: cards
                    model: page.setup ? settings.presets : []
                    SettingsPresetCard {
                        width: (body.width - 28) / 3
                        preset: modelData
                        focused: index === page.cursor
                        onClicked: { page.cursor = index; settings.applyPreset(modelData.name) }
                    }
                }
            }

            // Every other tab.
            Repeater {
                id: lines
                model: page.rows
                Item {
                    id: line
                    readonly property var row: modelData
                    readonly property int rowIndex: index
                    width: body.width
                    // The whole row, its text included (a section title's top padding is inside the loader).
                    height: loader.height + 6
                    // The keys' place: only on a row they can act on (never a section title or a note).
                    readonly property bool marked: index === page.cursor && page.selectable(index)
                    Rectangle {
                        anchors.fill: parent
                        anchors.leftMargin: -14; anchors.rightMargin: -8
                        radius: Theme.radiusSmall + 2
                        color: line.marked ? Theme.accentSoft : "transparent"
                        border.color: line.marked ? Theme.accentLine : "transparent"
                        Behavior on color { ColorAnimation { duration: Theme.fast } }
                    }
                    Loader {
                        id: loader
                        width: parent.width
                        y: 3
                        opacity: line.row.enabled === false ? 0.4 : 1.0
                        enabled: line.row.enabled !== false
                        sourceComponent: line.row.kind === "toggle" ? toggleRow
                                       : line.row.kind === "choice" ? choiceRow
                                       : line.row.kind === "button" ? buttonRow
                                       : line.row.kind === "binding" ? bindingRow
                                       : line.row.kind === "section" ? sectionRow : noteRow
                    }
                }
            }
        }
    }
    // Beside the rows (never over a button), mirrored with them.
    Scroller {
        id: flickBar
        anchors { top: flick.top; bottom: flick.bottom; left: flick.right; leftMargin: 4 }
    }

    Component {
        id: toggleRow
        Toggle {
            readonly property var row: parent.parent.row
            label: row.title; hint: row.hint; checked: row.checked; own: row.own === true
            onToggled: (on) => { page.cursor = parent.parent.rowIndex; settings.set(row.key, on) }
            onReset: settings.clearOwnSetting(row.key)
        }
    }
    Component {
        id: choiceRow
        Choice {
            readonly property var row: parent.parent.row
            label: row.title; hint: row.hint; options: row.options; current: row.value; own: row.own === true
            onChosen: (value) => { page.cursor = parent.parent.rowIndex; settings.set(row.key, value) }
            onReset: settings.clearOwnSetting(row.key)
        }
    }
    Component {
        id: buttonRow
        SettingsButtonRow {
            readonly property var row: parent.parent.row
            label: row.title; hint: row.hint; buttonText: row.label; danger: row.danger === true
            onClicked: { page.cursor = parent.parent.rowIndex; page.run(row.action, row.arg) }
        }
    }
    Component {
        id: bindingRow
        SettingsBinding {
            row: parent.parent.row
            onCapture: (slot) => { page.cursor = parent.parent.rowIndex; page.startCapture(row.action, slot) }
            onClear: (slot) => settings.clearBinding(row.action, slot)
            onPadChosen: (button) => settings.setPad(row.action, button)
            onReset: settings.clearOwn(row.action)
        }
    }
    Component {
        id: sectionRow
        Text {
            readonly property var row: parent.parent.row
            width: parent ? parent.width : 600
            topPadding: 14
            text: row.title; color: Theme.accent; font.family: Theme.strongFont; font.pixelSize: 12; font.letterSpacing: Theme.tracking(3)
        }
    }
    Component {
        id: noteRow
        Text {
            readonly property var row: parent.parent.row
            width: parent ? parent.width : 600
            text: row.text || ""; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 12
            wrapMode: Text.WordWrap; lineHeight: 1.3
        }
    }

    // The keys, for the device in use (a message the model could not save is the window's message box).
    KeyHint {
        id: hints
        anchors { left: parent.left; bottom: parent.bottom }
        entries: [
            { action: "views", text: qsTr("TABS") }, { action: "choose", text: qsTr("MOVE") },
            { action: "accept", text: page.setup ? qsTr("APPLY") : qsTr("CHANGE") }
        ]
    }

    // While a binding waits for its key: every key, mouse button and wheel step on the page is the binding.
    Item {
        id: catcher
        anchors.fill: parent
        visible: settings.capturing !== ""
        z: 10
        Keys.onPressed: (event) => {
            event.accepted = true
            if (!event.isAutoRepeat) settings.captureKey(event.key, event.nativeScanCode, event.modifiers)
        }
        Timer { id: arming; interval: 200 }  // the click that started the capture is not its binding
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.AllButtons
            onPressed: (mouse) => {
                if (arming.running) return
                var names = {}
                names[Qt.LeftButton] = "left"; names[Qt.RightButton] = "right"; names[Qt.MiddleButton] = "middle"
                names[Qt.BackButton] = "x1"; names[Qt.ForwardButton] = "x2"
                if (names[mouse.button] !== undefined) settings.captureMouse(names[mouse.button])
            }
            onWheel: (wheel) => {
                if (!arming.running && wheel.angleDelta.y !== 0)
                    settings.captureMouse(wheel.angleDelta.y > 0 ? "wheel_up" : "wheel_down")
            }
        }
    }
}
