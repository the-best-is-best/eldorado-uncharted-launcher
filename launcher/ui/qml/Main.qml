// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (C) 2026 Michelle Raouf
// The launcher's window: the rail on the left (Home, Saves, Trophies, Gallery, Settings; at its foot Update when a
// release is ready, Logs and Quit) and the chosen screen. An action of the rail's foot is also a screen with one
// button, so Tab and a controller reach it; a click on it runs the action at once.
// Keys: Up/Down/Enter go to the screen (its up(), down(), accept(), and optional moveLeft(), moveRight(), remove()),
// Tab / Shift+Tab change screen, Escape goes back home (and asks to quit from there).
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "pages"

ApplicationWindow {
    id: window
    // Arabic: the whole window right to left (the rail on the right), the dialogs in the overlay too.
    LayoutMirroring.enabled: i18n.rtl
    LayoutMirroring.childrenInherit: true
    width: 1280
    height: 720
    minimumWidth: 960
    minimumHeight: 540
    // Started from a game's shortcut (--play): no window, the launcher ends with the game.
    visible: !launcher.direct
    color: Theme.base

    // A screen has a page in the stack; an action is shown by the one action page (its name says which).
    readonly property var screens: [
        { name: qsTr("HOME"), page: 0 }, { name: qsTr("SAVES"), page: 1 }, { name: qsTr("TROPHIES"), page: 2 },
        { name: qsTr("GALLERY"), page: 3 }, { name: qsTr("SETTINGS"), page: 4 },
        { name: qsTr("UPDATE"), action: "update" }, { name: qsTr("LOGS"), action: "logs" }, { name: qsTr("QUIT"), action: "quit" }
    ]
    readonly property int firstAction: 5
    property int screen: 0

    // The chosen game's color for the whole window, eased from the last one.
    readonly property color gameAccent: launcher.games.length > 0 && launcher.games[launcher.selectedIndex]
                                        ? Theme.accentOf(launcher.games[launcher.selectedIndex].key) : Theme.gold
    onGameAccentChanged: { accentFade.stop(); accentFade.to = gameAccent; accentFade.start() }
    Component.onCompleted: Theme.accent = gameAccent
    // Arabic letters join and East Asian signs stand apart: no letter spacing there (Theme.tracking).
    Binding { target: Theme; property: "joinedScript"; value: i18n.unspaced }
    ColorAnimation { id: accentFade; target: Theme; property: "accent"; duration: Theme.slow; easing.type: Easing.InOutQuad }

    // While a game's window is up the launcher steps aside, and comes back when the game ends.
    Connections {
        target: launcher
        function onChanged() {
            if (launcher.gameWindowOpen && window.visible)
                window.hide()
            else if (!launcher.gameWindowOpen && !window.visible && !launcher.direct) {
                window.show()
                window.raise()
                window.requestActivate()
            }
        }
    }
    // The update's screen goes with the update.
    Connections {
        target: app
        function onChanged() { if (!window.available(window.screen)) window.screen = 0 }
    }

    // The controller: the same moves as the keys. Off while a game runs (no polling then).
    Connections {
        target: typeof gamepad !== "undefined" ? gamepad : null
        function onAction(name) {
            if (name === "back") window.back()
            else if (name === "next") window.nextScreen(1)
            else if (name === "previous") window.nextScreen(-1)
            else if (name === "play") { window.screen = 0; homePage.accept() }
            else if (name === "left" || name === "right") window.sideways(name)
            else window.call(name)
        }
    }
    onVisibleChanged: if (typeof gamepad !== "undefined") gamepad.setActive(visible)

    function available(index) { return window.screens[index].action !== "update" || app.updateAvailable }
    function nextScreen(step) {
        if (launcher.running) return
        var count = window.screens.length
        var next = window.screen
        do next = (next + count + step) % count; while (!window.available(next))
        window.screen = next
    }
    function back() {
        if (window.screen === 0) app.quit(true)
        else window.screen = 0
    }
    // Left and right as the player sees them: right to left (Arabic) the next tab or item is on the left, so the
    // arrow keeps pointing where the move goes.
    function sideways(arrow) {
        var forward = (arrow === "right") !== i18n.rtl
        window.call(forward ? "moveRight" : "moveLeft")
    }
    function current() { return stack.children[stack.currentIndex] }
    function call(name) { var page = current(); if (page && typeof page[name] === "function") page[name]() }

    Item {
        anchors.fill: parent
        LayoutMirroring.enabled: i18n.rtl
        LayoutMirroring.childrenInherit: true
        focus: true
        Keys.onUpPressed: window.call("up")
        Keys.onDownPressed: window.call("down")
        Keys.onLeftPressed: window.sideways("left")
        Keys.onRightPressed: window.sideways("right")
        Keys.onReturnPressed: window.call("accept")
        Keys.onEnterPressed: window.call("accept")
        Keys.onDeletePressed: window.call("remove")
        Keys.onPressed: if (typeof gamepad !== "undefined") gamepad.keyboardUsed()
        Keys.onTabPressed: window.nextScreen(1)
        Keys.onBacktabPressed: window.nextScreen(-1)
        Keys.onEscapePressed: window.back()

        // One item of the rail: a screen's name, or an action's (UPDATE in its own color while a release waits).
        // The chosen one sits on a soft pill of the game's color with a bright bar at its edge.
        component RailItem: Rectangle {
            id: railItem
            property int at: 0
            readonly property var item: window.screens[at]
            readonly property bool chosen: at === window.screen
            visible: window.available(at)
            width: 168; height: 42; radius: Theme.radiusSmall
            color: chosen ? Theme.accentSoft : (railArea.containsMouse && railArea.enabled ? Theme.glassHover : "transparent")
            Behavior on color { ColorAnimation { duration: Theme.fast } }
            Rectangle {
                anchors { left: parent.left; leftMargin: 6; verticalCenter: parent.verticalCenter }
                width: 3; radius: 2
                height: railItem.chosen ? 20 : 0
                color: Theme.accent
                Behavior on height { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
            }
            Text {
                anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                text: railItem.item.name
                color: railItem.chosen ? Theme.ink : railItem.item.action === "update" ? Theme.update
                     : railArea.containsMouse ? Theme.ink : Theme.dim
                font.family: railItem.chosen ? Theme.strongFont : Theme.bodyFont
                font.pixelSize: 13; font.letterSpacing: Theme.tracking(3)
                Behavior on color { ColorAnimation { duration: Theme.fast } }
            }
            MouseArea {
                id: railArea
                anchors.fill: parent
                hoverEnabled: true
                enabled: railItem.item.action === "quit" || !launcher.running || railItem.at === 0
                onClicked: {
                    if (railItem.item.action !== undefined) actionPage.run(railItem.item.action)
                    else window.screen = railItem.at
                }
            }
        }

        // The rail.
        Rectangle {
            id: rail
            width: 212
            anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
            color: Theme.rail
            Rectangle { anchors { top: parent.top; bottom: parent.bottom; right: parent.right } width: 1; color: Theme.glassEdge }
            Column {
                anchors { left: parent.left; leftMargin: 22; top: parent.top; topMargin: 30 }
                spacing: 4
                Text { leftPadding: 2; text: "EL DORADO"; color: Theme.gold; font.family: Theme.titleFont; font.pixelSize: 22; font.letterSpacing: Theme.tracking(4) }
                Text { leftPadding: 2; text: "UNCHARTED COLLECTION"; color: Theme.faint; font.family: Theme.bodyFont; font.pixelSize: 10; font.letterSpacing: Theme.tracking(2) }
                Item { width: 1; height: 18 }
                ProfileSwitch {}
                Item { width: 1; height: 18 }
                Repeater {
                    model: window.firstAction
                    RailItem { at: index }
                }
            }
            Column {
                anchors { left: parent.left; leftMargin: 22; bottom: railHints.top; bottomMargin: 22 }
                spacing: 4
                Repeater {
                    model: window.screens.length - window.firstAction
                    RailItem { at: window.firstAction + index }
                }
            }
            // The keys of the device in use (KeyHint follows it).
            Column {
                id: railHints
                anchors { left: parent.left; leftMargin: 26; bottom: parent.bottom; bottomMargin: 20 }
                spacing: 8
                KeyHint { entries: [{ action: "next", text: qsTr("SCREENS") }] }
                KeyHint { entries: [{ action: "back", text: qsTr("HOME") }] }
            }
        }

        StackLayout {
            id: stack
            anchors { top: parent.top; bottom: parent.bottom; left: rail.right; right: parent.right }
            currentIndex: window.screens[window.screen].page !== undefined ? window.screens[window.screen].page
                                                                           : window.firstAction
            HomePage { id: homePage }
            SavesPage {}
            TrophiesPage {}
            GalleryPage {}
            SettingsPage {}
            ActionPage { id: actionPage; action: window.screens[window.screen].action || "" }
        }
    }

    // The first start (no game folder yet, or the settings never set up): over everything until START.
    Loader {
        anchors.fill: parent
        LayoutMirroring.enabled: i18n.rtl
        LayoutMirroring.childrenInherit: true
        active: app.firstStart
        sourceComponent: Rectangle {
            color: Theme.base
            FirstStartPage { anchors.fill: parent }
        }
    }

    // Folder and file pickers, questions, every model's messages, and the long actions' progress.
    AppDialogs {}
}
